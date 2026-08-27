--
-- PostgreSQL database dump
--

\restrict IxJAag1dp5VPpb2yLflldxNlpRgLgbxw4bNaJgN14JPMPsvEZf38gNDfXMG6gtX

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: conversationtype; Type: TYPE; Schema: public; Owner: chatuser
--

CREATE TYPE public.conversationtype AS ENUM (
    'PERSONAL',
    'GROUP'
);


ALTER TYPE public.conversationtype OWNER TO chatuser;

--
-- Name: language; Type: TYPE; Schema: public; Owner: chatuser
--

CREATE TYPE public.language AS ENUM (
    'EN',
    'HI'
);


ALTER TYPE public.language OWNER TO chatuser;

--
-- Name: messagetype; Type: TYPE; Schema: public; Owner: chatuser
--

CREATE TYPE public.messagetype AS ENUM (
    'CHAT',
    'SYSTEM'
);


ALTER TYPE public.messagetype OWNER TO chatuser;

--
-- Name: participantrole; Type: TYPE; Schema: public; Owner: chatuser
--

CREATE TYPE public.participantrole AS ENUM (
    'ADMIN',
    'OWNER',
    'MEMBER'
);


ALTER TYPE public.participantrole OWNER TO chatuser;

--
-- Name: theme; Type: TYPE; Schema: public; Owner: chatuser
--

CREATE TYPE public.theme AS ENUM (
    'SYSTEM',
    'LIGHT',
    'DARK'
);


ALTER TYPE public.theme OWNER TO chatuser;

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: chatuser
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'USER',
    'MODERATOR'
);


ALTER TYPE public.userrole OWNER TO chatuser;

--
-- Name: visibility; Type: TYPE; Schema: public; Owner: chatuser
--

CREATE TYPE public.visibility AS ENUM (
    'EVERYONE',
    'CONTACTS',
    'NOBODY'
);


ALTER TYPE public.visibility OWNER TO chatuser;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO chatuser;

--
-- Name: conversation_participants; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.conversation_participants (
    conversation_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role public.participantrole NOT NULL,
    joined_at timestamp with time zone NOT NULL,
    last_read_message_id uuid,
    id uuid NOT NULL
);


ALTER TABLE public.conversation_participants OWNER TO chatuser;

--
-- Name: conversations; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.conversations (
    type public.conversationtype NOT NULL,
    name character varying(100),
    created_at timestamp with time zone NOT NULL,
    is_deleted boolean NOT NULL,
    id uuid NOT NULL,
    description character varying(500),
    avatar_url character varying(500),
    settings jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE public.conversations OWNER TO chatuser;

--
-- Name: message_delete_state; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.message_delete_state (
    message_id uuid NOT NULL,
    user_id uuid NOT NULL,
    deleted_at timestamp with time zone,
    id uuid NOT NULL
);


ALTER TABLE public.message_delete_state OWNER TO chatuser;

--
-- Name: message_reactions; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.message_reactions (
    message_id uuid NOT NULL,
    user_id uuid NOT NULL,
    reaction character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.message_reactions OWNER TO chatuser;

--
-- Name: message_receipts; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.message_receipts (
    message_id uuid NOT NULL,
    user_id uuid NOT NULL,
    delivered_at timestamp with time zone,
    read_at timestamp with time zone,
    id uuid NOT NULL
);


ALTER TABLE public.message_receipts OWNER TO chatuser;

--
-- Name: messages; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.messages (
    conversation_id uuid NOT NULL,
    sender_id uuid NOT NULL,
    type public.messagetype NOT NULL,
    message text NOT NULL,
    edited_at timestamp with time zone,
    is_deleted_global boolean NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    reply_to_message_id uuid
);


ALTER TABLE public.messages OWNER TO chatuser;

--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.refresh_tokens (
    user_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    device_name character varying(100),
    ip_address character varying(255),
    expires_at timestamp without time zone NOT NULL,
    revoked boolean NOT NULL,
    id uuid NOT NULL,
    last_sync_at timestamp with time zone,
    device_id character varying(255)
);


ALTER TABLE public.refresh_tokens OWNER TO chatuser;

--
-- Name: user_profiles; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.user_profiles (
    user_id uuid NOT NULL,
    display_name character varying(100),
    bio text,
    date_of_birth date,
    custom_status character varying(100),
    avatar_url character varying(500),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.user_profiles OWNER TO chatuser;

--
-- Name: user_settings; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.user_settings (
    user_id uuid NOT NULL,
    theme public.theme NOT NULL,
    language public.language NOT NULL,
    notifications_enabled boolean NOT NULL,
    message_notifications boolean NOT NULL,
    mention_notifications boolean NOT NULL,
    sound_enabled boolean NOT NULL,
    profile_visibility public.visibility NOT NULL,
    avatar_visibility public.visibility NOT NULL,
    last_seen_visibility public.visibility NOT NULL,
    read_receipts_enabled boolean NOT NULL,
    enter_to_send boolean NOT NULL,
    media_auto_download boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.user_settings OWNER TO chatuser;

--
-- Name: users; Type: TABLE; Schema: public; Owner: chatuser
--

CREATE TABLE public.users (
    username character varying(50) NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    role public.userrole NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.users OWNER TO chatuser;

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: conversation_participants conversation_participants_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT conversation_participants_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: message_delete_state message_delete_state_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_delete_state
    ADD CONSTRAINT message_delete_state_pkey PRIMARY KEY (id);


--
-- Name: message_reactions message_reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_reactions
    ADD CONSTRAINT message_reactions_pkey PRIMARY KEY (id);


--
-- Name: message_receipts message_receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_receipts
    ADD CONSTRAINT message_receipts_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: conversation_participants uq_conversation_participant; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT uq_conversation_participant UNIQUE (conversation_id, user_id);


--
-- Name: message_delete_state uq_message_delete_state; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_delete_state
    ADD CONSTRAINT uq_message_delete_state UNIQUE (message_id, user_id);


--
-- Name: message_reactions uq_message_reaction; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_reactions
    ADD CONSTRAINT uq_message_reaction UNIQUE (message_id, user_id, reaction);


--
-- Name: message_receipts uq_message_receipt; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_receipts
    ADD CONSTRAINT uq_message_receipt UNIQUE (message_id, user_id);


--
-- Name: user_profiles user_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.user_profiles
    ADD CONSTRAINT user_profiles_pkey PRIMARY KEY (id);


--
-- Name: user_settings user_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.user_settings
    ADD CONSTRAINT user_settings_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_conversations_created_at; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_conversations_created_at ON public.conversations USING btree (created_at);


--
-- Name: ix_message_reactions_message; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_message_reactions_message ON public.message_reactions USING btree (message_id);


--
-- Name: ix_messages_conversation_id; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_messages_conversation_id ON public.messages USING btree (conversation_id);


--
-- Name: ix_messages_conversation_time; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_messages_conversation_time ON public.messages USING btree (conversation_id, "timestamp");


--
-- Name: ix_messages_reply_to_message_id; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_messages_reply_to_message_id ON public.messages USING btree (reply_to_message_id);


--
-- Name: ix_messages_sender_id; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_messages_sender_id ON public.messages USING btree (sender_id);


--
-- Name: ix_messages_timestamp; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_messages_timestamp ON public.messages USING btree ("timestamp");


--
-- Name: ix_receipts_user_read; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_receipts_user_read ON public.message_receipts USING btree (user_id, read_at);


--
-- Name: ix_refresh_tokens_device_id; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_refresh_tokens_device_id ON public.refresh_tokens USING btree (device_id);


--
-- Name: ix_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- Name: ix_user_profiles_user_id; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE UNIQUE INDEX ix_user_profiles_user_id ON public.user_profiles USING btree (user_id);


--
-- Name: ix_user_settings_user_id; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE UNIQUE INDEX ix_user_settings_user_id ON public.user_settings USING btree (user_id);


--
-- Name: ix_users_created_at; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE INDEX ix_users_created_at ON public.users USING btree (created_at);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: chatuser
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: conversation_participants conversation_participants_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT conversation_participants_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: conversation_participants conversation_participants_last_read_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT conversation_participants_last_read_message_id_fkey FOREIGN KEY (last_read_message_id) REFERENCES public.messages(id) ON DELETE SET NULL;


--
-- Name: conversation_participants conversation_participants_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT conversation_participants_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: message_delete_state message_delete_state_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_delete_state
    ADD CONSTRAINT message_delete_state_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id) ON DELETE CASCADE;


--
-- Name: message_delete_state message_delete_state_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_delete_state
    ADD CONSTRAINT message_delete_state_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: message_reactions message_reactions_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_reactions
    ADD CONSTRAINT message_reactions_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id) ON DELETE CASCADE;


--
-- Name: message_reactions message_reactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_reactions
    ADD CONSTRAINT message_reactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: message_receipts message_receipts_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_receipts
    ADD CONSTRAINT message_receipts_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id) ON DELETE CASCADE;


--
-- Name: message_receipts message_receipts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.message_receipts
    ADD CONSTRAINT message_receipts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: messages messages_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: messages messages_reply_to_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_reply_to_message_id_fkey FOREIGN KEY (reply_to_message_id) REFERENCES public.messages(id) ON DELETE SET NULL;


--
-- Name: messages messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_profiles user_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.user_profiles
    ADD CONSTRAINT user_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_settings user_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: chatuser
--

ALTER TABLE ONLY public.user_settings
    ADD CONSTRAINT user_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict IxJAag1dp5VPpb2yLflldxNlpRgLgbxw4bNaJgN14JPMPsvEZf38gNDfXMG6gtX

