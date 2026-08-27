#app/ws/manager.py
from collections import defaultdict
from dataclasses import dataclass, field
from fastapi import WebSocket
from app.redis_client import r
from app.redis.keys import RedisKeys
from app.services.cache_management.presence import presence_cache

import json
import time
from uuid6 import uuid7

@dataclass
class Connection:
	ws:WebSocket
	username:str
	connection_id:str
	joined_conversation:set[int] = field(default_factory=set)
	watched_users:set[int] = field(default_factory=set)

class ConnectionManager:
	def __init__(self):
		self.users:dict[int,list[Connection]] = defaultdict(list)
		self.local_conversations:dict[int,set[int]] = defaultdict(set)

	async def connect(self,user_id:str, username:str, ws:WebSocket)->str:
		await ws.accept()
		connection_id = str(uuid7())

		conn = Connection(
			ws = ws,
			username=username,
			connection_id=connection_id
			)

		self.users[user_id].append(conn)
		redis_key = RedisKeys.user_connections(user_id)
		# redis_key = f"user:{user_id}:connections"

		await r.sadd(
			redis_key,
			connection_id
		)
		count = await r.scard(redis_key)
		if count == 1:
			await r.sadd(
			"online_users",
			user_id
			)
			await r.publish(
				"presence",
				json.dumps({
					"event":"presence",
					"user_id":user_id,
					"online":True,
				})
			)
	
	def _get_conv(self,user_id:str,ws:WebSocket):
		for con in self.users.get(user_id,[]):
			if con.ws == ws:
				return con
		return None

	async def join_conversation(self,conversation_id:str,user_id:str,ws:WebSocket):
		con = self._get_conv(user_id,ws)
		if not con:
			return

		con.joined_conversation.add(conversation_id)
		self.local_conversations[conversation_id].add(user_id)

	def get_local_members(self,conversation_id:str):
		return self.local_conversations.get(conversation_id,set())

	def _find_connection(self, user_id: str, ws: WebSocket):
		return self._get_conv(user_id, ws)


	async def disconnect(self,user_id:int,ws:WebSocket):
		connections = self.users.get(user_id,[])

		disconnected = None
		remaining = []

		for conn in connections:
			if conn.ws == ws:
				disconnected = conn
			else:
				remaining.append(conn)

		self.users[user_id] = remaining
		# If no connections in users mapped to user_id then remove it from the memory
		if not self.users[user_id]:
			self.users.pop(user_id,None)

		if not disconnected:
			return


		for conv_id in list(disconnected.joined_conversation):
			self.local_conversations[conv_id].discard(user_id)
			if not self.local_conversations[conv_id]:
				self.local_conversations.pop(conv_id,None)

		disconnected.joined_conversation.clear()
		redis_key = RedisKeys.user_connections(user_id)
		# redis_key = f"user:{user_id}:connections"
		try:
			await r.srem(
				redis_key,
				disconnected.connection_id
			)
			remaining_count = await r.scard(redis_key)
			if remaining_count == 0:
				await r.delete(redis_key)
				await presence_cache.set_offline(str(user_id))
				await r.publish(
					"presence",
					json.dumps({
						"event": "presence",
						"user_id": user_id,
						"online": False,
						"last_seen": int(time.time()),
					})
				)
		except Exception as e:
			print(f"Error removing connection from Redis: {e}")


		for target_user_id in list(disconnected.watched_users):
			try:
				await presence_cache.unwatch(
					watcher_id=user_id,
					target_user_id=target_user_id,
				)
			except Exception as e:
				print(
					f"Failed to unwatch {target_user_id} for {user_id}: {e}"
				)

		disconnected.watched_users.clear()



	async def send_to_user(self, user_id:str,payload:dict):
		connections = self.users.get(user_id,None)
		if connections is None:
			return

		dead = []

		for con in connections:
			try:
				await con.ws.send_json(payload)
			except Exception:
				dead.append(con)

		for con in dead:
			try:
				self.users[user_id].remove(con)
				redis_key = RedisKeys.user_connections(user_id)
				await r.srem(redis_key,con.connection_id)
			except Exception:
				await self.disconnect(user_id, con.ws)
		if(user_id in self.users and not self.users[user_id]):
			self.users.pop(user_id,None)

manager = ConnectionManager()