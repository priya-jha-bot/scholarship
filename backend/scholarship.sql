--
-- PostgreSQL database dump
--

\restrict PDfWAdQZkgmoN8cLt34YsyEA0IV2SsfaBc8faVdMTpl37HdZeLGwQMRFuXUbwet

-- Dumped from database version 16.16 (Debian 16.16-1.pgdg13+1)
-- Dumped by pg_dump version 16.16 (Debian 16.16-1.pgdg13+1)

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

ALTER TABLE IF EXISTS ONLY public.status_history DROP CONSTRAINT IF EXISTS fk_status_history_application_id_applications;
ALTER TABLE IF EXISTS ONLY public.status_history DROP CONSTRAINT IF EXISTS fk_status_history_actor_id_users;
ALTER TABLE IF EXISTS ONLY public.scholarship_rounds DROP CONSTRAINT IF EXISTS fk_scholarship_rounds_scholarship_id_scholarships;
ALTER TABLE IF EXISTS ONLY public.review_scores DROP CONSTRAINT IF EXISTS fk_review_scores_reviewer_id_users;
ALTER TABLE IF EXISTS ONLY public.review_scores DROP CONSTRAINT IF EXISTS fk_review_scores_application_id_applications;
ALTER TABLE IF EXISTS ONLY public.documents DROP CONSTRAINT IF EXISTS fk_documents_application_id_applications;
ALTER TABLE IF EXISTS ONLY public.disbursements DROP CONSTRAINT IF EXISTS fk_disbursements_application_id_applications;
ALTER TABLE IF EXISTS ONLY public.bank_details DROP CONSTRAINT IF EXISTS fk_bank_details_application_id_applications;
ALTER TABLE IF EXISTS ONLY public.applications DROP CONSTRAINT IF EXISTS fk_applications_student_id_users;
ALTER TABLE IF EXISTS ONLY public.applications DROP CONSTRAINT IF EXISTS fk_applications_scholarship_id_scholarships;
ALTER TABLE IF EXISTS ONLY public.applications DROP CONSTRAINT IF EXISTS fk_applications_round_id_scholarship_rounds;
DROP INDEX IF EXISTS public.ix_status_history_application;
DROP INDEX IF EXISTS public.ix_rounds_scholarship;
DROP INDEX IF EXISTS public.ix_review_scores_application;
DROP INDEX IF EXISTS public.ix_documents_sha256;
DROP INDEX IF EXISTS public.ix_applications_student;
DROP INDEX IF EXISTS public.ix_applications_status;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS uq_users_email;
ALTER TABLE IF EXISTS ONLY public.scholarship_rounds DROP CONSTRAINT IF EXISTS uq_scholarship_rounds_scholarship_id;
ALTER TABLE IF EXISTS ONLY public.applications DROP CONSTRAINT IF EXISTS uq_one_application_per_round;
ALTER TABLE IF EXISTS ONLY public.documents DROP CONSTRAINT IF EXISTS uq_documents_application_id;
ALTER TABLE IF EXISTS ONLY public.disbursements DROP CONSTRAINT IF EXISTS uq_disbursements_application_id;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS pk_users;
ALTER TABLE IF EXISTS ONLY public.status_history DROP CONSTRAINT IF EXISTS pk_status_history;
ALTER TABLE IF EXISTS ONLY public.scholarships DROP CONSTRAINT IF EXISTS pk_scholarships;
ALTER TABLE IF EXISTS ONLY public.scholarship_rounds DROP CONSTRAINT IF EXISTS pk_scholarship_rounds;
ALTER TABLE IF EXISTS ONLY public.review_scores DROP CONSTRAINT IF EXISTS pk_review_scores;
ALTER TABLE IF EXISTS ONLY public.documents DROP CONSTRAINT IF EXISTS pk_documents;
ALTER TABLE IF EXISTS ONLY public.disbursements DROP CONSTRAINT IF EXISTS pk_disbursements;
ALTER TABLE IF EXISTS ONLY public.bank_details DROP CONSTRAINT IF EXISTS pk_bank_details;
ALTER TABLE IF EXISTS ONLY public.applications DROP CONSTRAINT IF EXISTS pk_applications;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
ALTER TABLE IF EXISTS public.status_history ALTER COLUMN id DROP DEFAULT;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.status_history_id_seq;
DROP TABLE IF EXISTS public.status_history;
DROP TABLE IF EXISTS public.scholarships;
DROP TABLE IF EXISTS public.scholarship_rounds;
DROP TABLE IF EXISTS public.review_scores;
DROP TABLE IF EXISTS public.documents;
DROP TABLE IF EXISTS public.disbursements;
DROP TABLE IF EXISTS public.bank_details;
DROP TABLE IF EXISTS public.applications;
DROP TABLE IF EXISTS public.alembic_version;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.applications (
    id uuid NOT NULL,
    student_id uuid NOT NULL,
    scholarship_id uuid NOT NULL,
    round_id uuid NOT NULL,
    status character varying(24) NOT NULL,
    declaration_accepted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_applications_status_valid CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'VERIFIED'::character varying, 'REJECTED_BY_ADMIN'::character varying, 'CHANGES_REQUESTED'::character varying, 'APPROVED'::character varying, 'REJECTED'::character varying, 'WITHDRAWN'::character varying, 'DISBURSED'::character varying])::text[])))
);


--
-- Name: bank_details; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bank_details (
    application_id uuid NOT NULL,
    account_holder_name character varying(120) NOT NULL,
    account_number_enc text NOT NULL,
    ifsc_enc text NOT NULL,
    account_last4 character varying(4) NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: disbursements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.disbursements (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    amount integer NOT NULL,
    reference character varying(80) NOT NULL,
    disbursed_at timestamp with time zone NOT NULL
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    doc_type character varying(40) NOT NULL,
    filename character varying(160) NOT NULL,
    stored_path character varying(300) NOT NULL,
    content_type character varying(60) NOT NULL,
    size_bytes integer NOT NULL,
    sha256 character varying(64) NOT NULL,
    check_status character varying(10) NOT NULL,
    check_note character varying(200) NOT NULL,
    uploaded_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_documents_check_status_valid CHECK (((check_status)::text = ANY ((ARRAY['pending'::character varying, 'ok'::character varying, 'flagged'::character varying])::text[])))
);


--
-- Name: review_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review_scores (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    reviewer_id uuid NOT NULL,
    academic integer NOT NULL,
    financial_need integer NOT NULL,
    other integer NOT NULL,
    total integer NOT NULL,
    decision character varying(24) NOT NULL,
    remarks text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_review_scores_academic_range CHECK (((academic >= 0) AND (academic <= 40))),
    CONSTRAINT ck_review_scores_need_range CHECK (((financial_need >= 0) AND (financial_need <= 40))),
    CONSTRAINT ck_review_scores_other_range CHECK (((other >= 0) AND (other <= 20)))
);


--
-- Name: scholarship_rounds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scholarship_rounds (
    id uuid NOT NULL,
    scholarship_id uuid NOT NULL,
    label character varying(40) NOT NULL,
    opens_on date NOT NULL,
    closes_on date NOT NULL
);


--
-- Name: scholarships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scholarships (
    id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    amount integer NOT NULL,
    deadline date NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_scholarships_amount_positive CHECK ((amount > 0))
);


--
-- Name: status_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.status_history (
    id integer NOT NULL,
    application_id uuid NOT NULL,
    status character varying(24) NOT NULL,
    at timestamp with time zone NOT NULL,
    remarks text NOT NULL,
    actor_id uuid,
    CONSTRAINT ck_status_history_status_valid CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'SUBMITTED'::character varying, 'VERIFIED'::character varying, 'REJECTED_BY_ADMIN'::character varying, 'CHANGES_REQUESTED'::character varying, 'APPROVED'::character varying, 'REJECTED'::character varying, 'WITHDRAWN'::character varying, 'DISBURSED'::character varying])::text[])))
);


--
-- Name: status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.status_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: status_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.status_history_id_seq OWNED BY public.status_history.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    full_name character varying(120) NOT NULL,
    email character varying(254) NOT NULL,
    password_hash character varying(100) NOT NULL,
    role character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_users_role_valid CHECK (((role)::text = ANY ((ARRAY['student'::character varying, 'admin'::character varying, 'reviewer'::character varying])::text[])))
);


--
-- Name: status_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_history ALTER COLUMN id SET DEFAULT nextval('public.status_history_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
001
\.


--
-- Data for Name: applications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.applications (id, student_id, scholarship_id, round_id, status, declaration_accepted_at, created_at, updated_at) FROM stdin;
473701cb-e86b-46c1-8c8e-5b3f502116fb	0b31e95f-ad65-4c59-b2bf-bf567b79e7cb	7f3042ec-bd69-4c2f-b86d-e8650b76c0d7	e7f33d0f-403a-492b-a743-39ea941b66c8	SUBMITTED	\N	2026-11-14 12:36:56.399935+00	2026-11-15 12:36:56.399935+00
82a1ee8e-a7c5-4098-822a-3582e7ea0c32	0b31e95f-ad65-4c59-b2bf-bf567b79e7cb	55127692-08ee-4d1c-aeec-c8d9a2c8f6c2	3d59a79d-1ea3-4051-b4f2-c47d81cb356f	VERIFIED	\N	2026-11-13 12:36:56.417004+00	2026-11-15 12:36:56.417004+00
26d0a84b-aaf9-4ad9-a667-e60e07d02457	0b31e95f-ad65-4c59-b2bf-bf567b79e7cb	faf8cfcd-34b8-422c-86de-3638be76c741	42014c02-eabd-42aa-a72b-a71f4197d405	CHANGES_REQUESTED	\N	2026-11-12 12:36:56.423234+00	2026-11-15 12:36:56.423234+00
992ef476-62f2-4aeb-ba05-7cbc5e934763	5febe88a-23a7-4062-aafd-1ee93487d896	7f3042ec-bd69-4c2f-b86d-e8650b76c0d7	e7f33d0f-403a-492b-a743-39ea941b66c8	APPROVED	\N	2026-11-12 12:36:56.428692+00	2026-11-15 12:36:56.428692+00
bc614adf-cc08-43f1-9f1c-749822f4e92e	5febe88a-23a7-4062-aafd-1ee93487d896	55127692-08ee-4d1c-aeec-c8d9a2c8f6c2	3d59a79d-1ea3-4051-b4f2-c47d81cb356f	DRAFT	\N	2026-11-15 12:36:56.435976+00	2026-11-15 12:36:56.435976+00
9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	fcaf6b93-ea78-4581-b355-4c47e77b50be	55127692-08ee-4d1c-aeec-c8d9a2c8f6c2	3d59a79d-1ea3-4051-b4f2-c47d81cb356f	REJECTED	\N	2026-11-12 12:36:56.438552+00	2026-11-15 12:36:56.438552+00
b535dc9d-32cc-4c65-9f12-1fe58c3b1a50	adb77344-301a-43e9-9da9-08131c21f51f	55127692-08ee-4d1c-aeec-c8d9a2c8f6c2	3d59a79d-1ea3-4051-b4f2-c47d81cb356f	DRAFT	\N	2026-11-17 13:39:20.505964+00	2026-11-17 13:39:20.505964+00
f9007016-21cd-4733-bdc3-de5ceb500f79	adb77344-301a-43e9-9da9-08131c21f51f	7f3042ec-bd69-4c2f-b86d-e8650b76c0d7	e7f33d0f-403a-492b-a743-39ea941b66c8	APPROVED	2026-11-17 12:55:47.992113+00	2026-11-17 12:52:23.236628+00	2026-11-17 13:46:10.425726+00
\.


--
-- Data for Name: bank_details; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bank_details (application_id, account_holder_name, account_number_enc, ifsc_enc, account_last4, updated_at) FROM stdin;
473701cb-e86b-46c1-8c8e-5b3f502116fb	Sara Student	gAAAAABq_EpoN8HnodRp218cKRqfUHtxHXAuOkHmfeh7qdk9xAY3o6Y1DoYjWHiT7fKDXKIQaQX6OH9OimgeNmo5mLZCr1yzCw==	gAAAAABq_Epozl69QXGOWKfliqm7IRhbb-HxuTFtRMPwwB_LzFGx5uGn9i7Vv6JjipNTt7DYC3bPMnwkbdBEeK7gKyBr3wDebg==	9012	2026-11-17 12:36:56.412844+00
82a1ee8e-a7c5-4098-822a-3582e7ea0c32	Sara Student	gAAAAABq_EpoKw8LDZlnkHC8pDwpzxNk0g33WbeccdOqcIBJpDcxGwK23mISFBJGPdd00pi-ZrwGHTyl45BwstaDINPQGdDpkw==	gAAAAABq_EpoB1Tf0YqftYUi8u-ysYJC2aEfOon7uUmDSPIP4NLDQnkl5DAKAF8SgJZgUGIvqr38zzpqXss3fvPHfYoxtvUM_Q==	9012	2026-11-17 12:36:56.42063+00
26d0a84b-aaf9-4ad9-a667-e60e07d02457	Sara Student	gAAAAABq_EpoExygRVYXGQDYj9WNq1kyT2Ex6j4WAqHaRcYKXaAV2eHtcAVo9W2o4wPn62kvzCHtMH6We71VXmhfaVB5B8dr2Q==	gAAAAABq_EponD9Mvzj4c-P5nB2KEP7RH2gEWMzJs8sA81X6XznoDbQF0nDGOjPusrh_x_J7upNzC_0cJYmoAEwJN6CxHgy0Uw==	9012	2026-11-17 12:36:56.426922+00
992ef476-62f2-4aeb-ba05-7cbc5e934763	Tara Student	gAAAAABq_EpovAVotQ4Z1tGFeJzfEg6o1Y8QJcaxEOaK9XsCaDaAB37pyXr_WcKTDX0cI38Dn72S_heUG6w7UKeM_vnYgxbxxA==	gAAAAABq_EpoehttreIjvuPaQ8hzT6_gIvnu8r077i-iUu44moULY5WDKiKxMZuhFJBWMo6HeiIzTXQMlKCheYbCqjtGZ9yzGw==	9012	2026-11-17 12:36:56.433904+00
9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	Uma Student	gAAAAABq_EpoJH-Zffch8TgHaNuVv-8MTNZjOOIa96BQjwrY0Tn4nKghRYeo_HjBn_Xp6Fln8FsvJFbm0-sJtgNZsGLUFumDjA==	gAAAAABq_EpoPRc_-UklKeev6ICd3b6SXQjhO4F_Vg-bEsVdTzVg_1YJbvBVuUC8zgNM0XBTxcIUuXpPMTfgj87fz9ComZcsUg==	9012	2026-11-17 12:36:56.442749+00
f9007016-21cd-4733-bdc3-de5ceb500f79	A.Bhattacharyya	gAAAAABq_E7N3LZ2WhF_XHYzSqmObHP-apFng48q7_QytG0Y89gA3K3xg92n6Z1yaJTJl4XyRlUMXMaIhc75UwenvK-TqxNacQ==	gAAAAABq_E7N-KK-sHkquF12ieDpTChzUIdXO94zJgACo7Av1tl8raMY4tPZquObjhKZD3C3MK-mJyH35Q7VmojHcKsdxosKJQ==	4234	2026-11-17 12:55:41.026519+00
\.


--
-- Data for Name: disbursements; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.disbursements (id, application_id, amount, reference, disbursed_at) FROM stdin;
\.


--
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documents (id, application_id, doc_type, filename, stored_path, content_type, size_bytes, sha256, check_status, check_note, uploaded_at) FROM stdin;
2df43b34-ff19-4310-8fe3-4ee2a1a75c06	473701cb-e86b-46c1-8c8e-5b3f502116fb	government_id	government_id.pdf	473701cb-e86b-46c1-8c8e-5b3f502116fb/b4d957bcf22d4c719dc59d8ca3527db2.pdf	application/pdf	406	d947d62944d73b551e0d221d3e442bb0c359b34812ac090729e231dab59b417e	ok		2026-11-17 12:36:56.413892+00
86623d13-502c-40bf-a5bd-4a209ce743b0	473701cb-e86b-46c1-8c8e-5b3f502116fb	address_proof	address_proof.pdf	473701cb-e86b-46c1-8c8e-5b3f502116fb/54652dad097445c0b047a5a99aee705f.pdf	application/pdf	406	1fa4125e25abb7628a2820ec525bb1335e10adea0f516eb9d5f48543c39de4f9	ok		2026-11-17 12:36:56.413892+00
aa3f7c15-c767-4e5c-9f2b-4cc473a963f7	473701cb-e86b-46c1-8c8e-5b3f502116fb	cancelled_cheque	cancelled_cheque.pdf	473701cb-e86b-46c1-8c8e-5b3f502116fb/8e17f1af57544708bc2ebdbaca3075fb.pdf	application/pdf	409	9dd51d1d3b50ced5db90a26e6cf5eb6be8b9eaa9c5f3b3be87c88225df41d1c5	ok		2026-11-17 12:36:56.413892+00
fff0c274-45f8-4de6-8579-6ea77812d593	82a1ee8e-a7c5-4098-822a-3582e7ea0c32	government_id	government_id.pdf	82a1ee8e-a7c5-4098-822a-3582e7ea0c32/d3fa48b4b48349dc95f0013d5199668d.pdf	application/pdf	406	ab0d9793bb36ec591aedebc936e9d479d0467e1942e0651031a8aa0b3ccb1cb8	ok		2026-11-17 12:36:56.42115+00
2abf931f-a07d-4337-9de9-894a479227a5	82a1ee8e-a7c5-4098-822a-3582e7ea0c32	address_proof	address_proof.pdf	82a1ee8e-a7c5-4098-822a-3582e7ea0c32/0ee4e5a0143949059666f1df0cbe177e.pdf	application/pdf	406	b82a9a74c50a4624403c63f4b554b0db2f5f9911a72e2a12de963d8ba57dd393	ok		2026-11-17 12:36:56.42115+00
965c7c23-a4b6-4556-b3b3-0cbb79fcdb96	82a1ee8e-a7c5-4098-822a-3582e7ea0c32	cancelled_cheque	cancelled_cheque.pdf	82a1ee8e-a7c5-4098-822a-3582e7ea0c32/2006e4d9405e44d1826f6549e39a3a26.pdf	application/pdf	409	c3b0d2f8175625f3d44cebde457970255b5a9a0be15bc8040adc8f06fa9a76b8	ok		2026-11-17 12:36:56.42115+00
9995f3c0-8f25-4b2f-9459-39bf30e26920	26d0a84b-aaf9-4ad9-a667-e60e07d02457	government_id	government_id.pdf	26d0a84b-aaf9-4ad9-a667-e60e07d02457/6f67875c0edd400f84269dfedc270132.pdf	application/pdf	406	03a86ed80c5fec034d470c08ae6b9fdd958235b15c48677db14dd2e14986aa73	ok		2026-11-17 12:36:56.427447+00
e3bde9c2-a751-472b-b14f-8b5c8e10b027	26d0a84b-aaf9-4ad9-a667-e60e07d02457	address_proof	address_proof.pdf	26d0a84b-aaf9-4ad9-a667-e60e07d02457/bffc3def5d6349cbb7e5c2dce3e0870d.pdf	application/pdf	406	1977c53aa0f29123512ab6047dfa346498fc03cb694992a32b2ba8808e061dc4	ok		2026-11-17 12:36:56.427447+00
93362a61-755a-4c4d-b1ee-8ef239470c85	26d0a84b-aaf9-4ad9-a667-e60e07d02457	cancelled_cheque	cancelled_cheque.pdf	26d0a84b-aaf9-4ad9-a667-e60e07d02457/98538ac8c4cb47e3aaeb81879b8fd2d0.pdf	application/pdf	409	b294a16466172adafdabc0678343e775c15a6160f2d5e0ce6ca8fc5a6a3974ed	ok		2026-11-17 12:36:56.427447+00
bc2861af-3ac4-43c4-ab17-ce160fdb33cb	992ef476-62f2-4aeb-ba05-7cbc5e934763	government_id	government_id.pdf	992ef476-62f2-4aeb-ba05-7cbc5e934763/a8012fabd47f4fbb929bbb33cce1ad19.pdf	application/pdf	406	65389fca9387f366989706a18d773340119a1e2cab13536730f5e35f46e2a1d5	ok		2026-11-17 12:36:56.434423+00
3f22c89c-6014-4e84-8c18-30e064af7c27	992ef476-62f2-4aeb-ba05-7cbc5e934763	address_proof	address_proof.pdf	992ef476-62f2-4aeb-ba05-7cbc5e934763/c92f66c5cd184fb8b155c2a30f4252b1.pdf	application/pdf	406	c5c1a84815c1fc7bbc2f71c6107c4d606d109b33e68d55b0341f428e21a496e0	ok		2026-11-17 12:36:56.434423+00
e7673758-dd6d-4c55-8831-715af53cbfa4	992ef476-62f2-4aeb-ba05-7cbc5e934763	cancelled_cheque	cancelled_cheque.pdf	992ef476-62f2-4aeb-ba05-7cbc5e934763/a5d0302b6a954a28888ecc29ec61e7cf.pdf	application/pdf	409	d0e198f64071b6967a6a4c122383b6407cd359b32bf5af9c662e0fd9bd73df9c	ok		2026-11-17 12:36:56.434423+00
bd292a5b-7154-4f85-88af-f0fb408acd72	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	government_id	government_id.pdf	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6/054e6b4efb5241f2b921460a880b882e.pdf	application/pdf	405	b693ddb5ba1caef69d97bc74b89484f62ad14c16f34be330f704345cfb17e8ff	ok		2026-11-17 12:36:56.44327+00
74dfabb8-e3c4-4bb3-98d6-56838cde06bb	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	address_proof	address_proof.pdf	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6/99e08d6a63364f81bddf588b070d15e3.pdf	application/pdf	405	a9146ef4c2ea1cf118404bd69aee6ae9839db07be0c55b576f12dd39f78a47a6	ok		2026-11-17 12:36:56.44327+00
a2162a8c-2bd6-4acb-8353-bb6d5966dd96	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	cancelled_cheque	cancelled_cheque.pdf	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6/5c50535c06b84d019bc77f1f2b953498.pdf	application/pdf	408	d7eb311b1534768b4bae5599744114f209154e92788e54094dd65fa1b1f21235	ok		2026-11-17 12:36:56.44327+00
85fc1ba5-3005-45bf-98d5-6520aee8cd20	f9007016-21cd-4733-bdc3-de5ceb500f79	government_id	399232d1280903481-maruti-plans-relaunch-alto-1000cc-k-series-engine-h_altofrontandsideview-184724420.jpg	f9007016-21cd-4733-bdc3-de5ceb500f79/2e2e326990924278b656a76a8ecb643e.jpg	image/jpeg	239604	7bbeb1d992cf72a24280ca82c08ca83176dc961723ae0e072b0f191a792315c5	ok		2026-11-17 12:53:32.67972+00
b810ff3e-c8f5-4995-a39c-d0772dbbccda	f9007016-21cd-4733-bdc3-de5ceb500f79	address_proof	ic-emoji.png	f9007016-21cd-4733-bdc3-de5ceb500f79/3b4a4925a1fd45d28a481d76b24ae703.png	image/png	87281	022ae28a65fea078b066b9727077f64feb738887084d15dd9c791007500bdbae	ok		2026-11-17 12:53:53.917321+00
cf028926-fbdb-4d57-bf58-d10dcd404e3f	f9007016-21cd-4733-bdc3-de5ceb500f79	cancelled_cheque	Screenshot 2025-12-03 150133.png	f9007016-21cd-4733-bdc3-de5ceb500f79/79f2be422c7e42d3b12a4031215d9b75.png	image/png	206769	87c5333cf5ce3cfaa0d5be2bba8cc4c08301134e253c27be1960ea8599b8c8c2	ok		2026-11-17 12:54:57.006308+00
\.


--
-- Data for Name: review_scores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.review_scores (id, application_id, reviewer_id, academic, financial_need, other, total, decision, remarks, created_at) FROM stdin;
8bd37d2c-51d6-4f36-88be-eae99d9a4283	992ef476-62f2-4aeb-ba05-7cbc5e934763	63b0bfe8-4401-4d1b-bde5-695702202854	35	30	15	80	APPROVED	Seed data	2026-11-17 12:36:56.43286+00
b8b14ece-41f8-486e-bb46-a8d8dfe0cebb	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	63b0bfe8-4401-4d1b-bde5-695702202854	12	10	5	27	REJECTED	Seed data	2026-11-17 12:36:56.441714+00
912a3261-d9b6-474a-9556-befd6018c098	f9007016-21cd-4733-bdc3-de5ceb500f79	63b0bfe8-4401-4d1b-bde5-695702202854	40	40	5	85	APPROVED		2026-11-17 13:46:10.427285+00
\.


--
-- Data for Name: scholarship_rounds; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scholarship_rounds (id, scholarship_id, label, opens_on, closes_on) FROM stdin;
e7f33d0f-403a-492b-a743-39ea941b66c8	7f3042ec-bd69-4c2f-b86d-e8650b76c0d7	2027	2026-10-18	2027-01-01
3d59a79d-1ea3-4051-b4f2-c47d81cb356f	55127692-08ee-4d1c-aeec-c8d9a2c8f6c2	2027	2026-10-18	2027-01-16
42014c02-eabd-42aa-a72b-a71f4197d405	faf8cfcd-34b8-422c-86de-3638be76c741	2027	2026-10-18	2027-01-31
\.


--
-- Data for Name: scholarships; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scholarships (id, title, description, amount, deadline, created_at) FROM stdin;
7f3042ec-bd69-4c2f-b86d-e8650b76c0d7	Merit Excellence Award	For top performers	50000	2027-01-01	2026-11-17 12:36:56.392749+00
55127692-08ee-4d1c-aeec-c8d9a2c8f6c2	Need-Based Support Grant	For families with limited income	30000	2027-01-16	2026-11-17 12:36:56.392749+00
faf8cfcd-34b8-422c-86de-3638be76c741	STEM Women Scholarship	Supporting women in STEM	40000	2027-01-31	2026-11-17 12:36:56.392749+00
\.


--
-- Data for Name: status_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.status_history (id, application_id, status, at, remarks, actor_id) FROM stdin;
1	473701cb-e86b-46c1-8c8e-5b3f502116fb	DRAFT	2026-11-14 12:36:56.399935+00		0b31e95f-ad65-4c59-b2bf-bf567b79e7cb
2	473701cb-e86b-46c1-8c8e-5b3f502116fb	SUBMITTED	2026-11-15 12:36:56.399935+00		0b31e95f-ad65-4c59-b2bf-bf567b79e7cb
3	82a1ee8e-a7c5-4098-822a-3582e7ea0c32	DRAFT	2026-11-13 12:36:56.417004+00		0b31e95f-ad65-4c59-b2bf-bf567b79e7cb
4	82a1ee8e-a7c5-4098-822a-3582e7ea0c32	SUBMITTED	2026-11-14 12:36:56.417004+00		0b31e95f-ad65-4c59-b2bf-bf567b79e7cb
5	82a1ee8e-a7c5-4098-822a-3582e7ea0c32	VERIFIED	2026-11-15 12:36:56.417004+00		d1e7428a-af64-4202-ac8c-ff571bfaa8f1
6	26d0a84b-aaf9-4ad9-a667-e60e07d02457	DRAFT	2026-11-12 12:36:56.423234+00		0b31e95f-ad65-4c59-b2bf-bf567b79e7cb
7	26d0a84b-aaf9-4ad9-a667-e60e07d02457	SUBMITTED	2026-11-13 12:36:56.423234+00		0b31e95f-ad65-4c59-b2bf-bf567b79e7cb
8	26d0a84b-aaf9-4ad9-a667-e60e07d02457	VERIFIED	2026-11-14 12:36:56.423234+00		d1e7428a-af64-4202-ac8c-ff571bfaa8f1
9	26d0a84b-aaf9-4ad9-a667-e60e07d02457	CHANGES_REQUESTED	2026-11-15 12:36:56.423234+00	Please upload a clearer cancelled cheque.	63b0bfe8-4401-4d1b-bde5-695702202854
10	992ef476-62f2-4aeb-ba05-7cbc5e934763	DRAFT	2026-11-12 12:36:56.428692+00		5febe88a-23a7-4062-aafd-1ee93487d896
11	992ef476-62f2-4aeb-ba05-7cbc5e934763	SUBMITTED	2026-11-13 12:36:56.428692+00		5febe88a-23a7-4062-aafd-1ee93487d896
12	992ef476-62f2-4aeb-ba05-7cbc5e934763	VERIFIED	2026-11-14 12:36:56.428692+00		d1e7428a-af64-4202-ac8c-ff571bfaa8f1
13	992ef476-62f2-4aeb-ba05-7cbc5e934763	APPROVED	2026-11-15 12:36:56.428692+00		63b0bfe8-4401-4d1b-bde5-695702202854
14	bc614adf-cc08-43f1-9f1c-749822f4e92e	DRAFT	2026-11-15 12:36:56.435976+00		5febe88a-23a7-4062-aafd-1ee93487d896
15	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	DRAFT	2026-11-12 12:36:56.438552+00		fcaf6b93-ea78-4581-b355-4c47e77b50be
16	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	SUBMITTED	2026-11-13 12:36:56.438552+00		fcaf6b93-ea78-4581-b355-4c47e77b50be
17	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	VERIFIED	2026-11-14 12:36:56.438552+00		d1e7428a-af64-4202-ac8c-ff571bfaa8f1
18	9e1150d0-5c6d-4a00-90ee-e880f8a1d5d6	REJECTED	2026-11-15 12:36:56.438552+00		63b0bfe8-4401-4d1b-bde5-695702202854
19	f9007016-21cd-4733-bdc3-de5ceb500f79	DRAFT	2026-11-17 12:52:23.237666+00	Draft created	adb77344-301a-43e9-9da9-08131c21f51f
20	f9007016-21cd-4733-bdc3-de5ceb500f79	SUBMITTED	2026-11-17 12:55:47.993159+00	Application submitted	adb77344-301a-43e9-9da9-08131c21f51f
21	b535dc9d-32cc-4c65-9f12-1fe58c3b1a50	DRAFT	2026-11-17 13:39:20.508593+00	Draft created	adb77344-301a-43e9-9da9-08131c21f51f
22	f9007016-21cd-4733-bdc3-de5ceb500f79	VERIFIED	2026-11-17 13:45:09.891278+00		d1e7428a-af64-4202-ac8c-ff571bfaa8f1
23	f9007016-21cd-4733-bdc3-de5ceb500f79	APPROVED	2026-11-17 13:46:10.428315+00		63b0bfe8-4401-4d1b-bde5-695702202854
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, full_name, email, password_hash, role, is_active, created_at) FROM stdin;
d1e7428a-af64-4202-ac8c-ff571bfaa8f1	Asha Admin	admin@example.com	$2b$12$JJaiy07Mih9kLCys4ghfXeyOY.So8H6Tsoj4uTTpAFkm0ohbAG0wi	admin	t	2026-11-17 12:36:56.395745+00
63b0bfe8-4401-4d1b-bde5-695702202854	Rahul Reviewer	reviewer@example.com	$2b$12$JJaiy07Mih9kLCys4ghfXeyOY.So8H6Tsoj4uTTpAFkm0ohbAG0wi	reviewer	t	2026-11-17 12:36:56.395745+00
0b31e95f-ad65-4c59-b2bf-bf567b79e7cb	Sara Student	student@example.com	$2b$12$JJaiy07Mih9kLCys4ghfXeyOY.So8H6Tsoj4uTTpAFkm0ohbAG0wi	student	t	2026-11-17 12:36:56.395745+00
5febe88a-23a7-4062-aafd-1ee93487d896	Tara Student	tara@example.com	$2b$12$JJaiy07Mih9kLCys4ghfXeyOY.So8H6Tsoj4uTTpAFkm0ohbAG0wi	student	t	2026-11-17 12:36:56.395745+00
fcaf6b93-ea78-4581-b355-4c47e77b50be	Uma Student	uma@example.com	$2b$12$JJaiy07Mih9kLCys4ghfXeyOY.So8H6Tsoj4uTTpAFkm0ohbAG0wi	student	t	2026-11-17 12:36:56.395745+00
adb77344-301a-43e9-9da9-08131c21f51f	Aishik Bhattacharyya	abcd@gmail.com	$2b$12$z1mF8uFHTF8ySOGP4CJy1eIx7tgPPLH0JYLiF8DeUHQhqMv5FMgLe	student	t	2026-11-17 12:52:18.661122+00
\.


--
-- Name: status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.status_history_id_seq', 23, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: applications pk_applications; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT pk_applications PRIMARY KEY (id);


--
-- Name: bank_details pk_bank_details; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_details
    ADD CONSTRAINT pk_bank_details PRIMARY KEY (application_id);


--
-- Name: disbursements pk_disbursements; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disbursements
    ADD CONSTRAINT pk_disbursements PRIMARY KEY (id);


--
-- Name: documents pk_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT pk_documents PRIMARY KEY (id);


--
-- Name: review_scores pk_review_scores; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_scores
    ADD CONSTRAINT pk_review_scores PRIMARY KEY (id);


--
-- Name: scholarship_rounds pk_scholarship_rounds; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scholarship_rounds
    ADD CONSTRAINT pk_scholarship_rounds PRIMARY KEY (id);


--
-- Name: scholarships pk_scholarships; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scholarships
    ADD CONSTRAINT pk_scholarships PRIMARY KEY (id);


--
-- Name: status_history pk_status_history; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_history
    ADD CONSTRAINT pk_status_history PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: disbursements uq_disbursements_application_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disbursements
    ADD CONSTRAINT uq_disbursements_application_id UNIQUE (application_id);


--
-- Name: documents uq_documents_application_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT uq_documents_application_id UNIQUE (application_id, doc_type);


--
-- Name: applications uq_one_application_per_round; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT uq_one_application_per_round UNIQUE (student_id, scholarship_id, round_id);


--
-- Name: scholarship_rounds uq_scholarship_rounds_scholarship_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scholarship_rounds
    ADD CONSTRAINT uq_scholarship_rounds_scholarship_id UNIQUE (scholarship_id, label);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: ix_applications_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_status ON public.applications USING btree (status);


--
-- Name: ix_applications_student; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_student ON public.applications USING btree (student_id);


--
-- Name: ix_documents_sha256; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_sha256 ON public.documents USING btree (sha256);


--
-- Name: ix_review_scores_application; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_scores_application ON public.review_scores USING btree (application_id);


--
-- Name: ix_rounds_scholarship; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rounds_scholarship ON public.scholarship_rounds USING btree (scholarship_id);


--
-- Name: ix_status_history_application; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_status_history_application ON public.status_history USING btree (application_id);


--
-- Name: applications fk_applications_round_id_scholarship_rounds; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_round_id_scholarship_rounds FOREIGN KEY (round_id) REFERENCES public.scholarship_rounds(id);


--
-- Name: applications fk_applications_scholarship_id_scholarships; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_scholarship_id_scholarships FOREIGN KEY (scholarship_id) REFERENCES public.scholarships(id);


--
-- Name: applications fk_applications_student_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_student_id_users FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: bank_details fk_bank_details_application_id_applications; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_details
    ADD CONSTRAINT fk_bank_details_application_id_applications FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: disbursements fk_disbursements_application_id_applications; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disbursements
    ADD CONSTRAINT fk_disbursements_application_id_applications FOREIGN KEY (application_id) REFERENCES public.applications(id);


--
-- Name: documents fk_documents_application_id_applications; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_application_id_applications FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: review_scores fk_review_scores_application_id_applications; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_scores
    ADD CONSTRAINT fk_review_scores_application_id_applications FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: review_scores fk_review_scores_reviewer_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_scores
    ADD CONSTRAINT fk_review_scores_reviewer_id_users FOREIGN KEY (reviewer_id) REFERENCES public.users(id);


--
-- Name: scholarship_rounds fk_scholarship_rounds_scholarship_id_scholarships; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scholarship_rounds
    ADD CONSTRAINT fk_scholarship_rounds_scholarship_id_scholarships FOREIGN KEY (scholarship_id) REFERENCES public.scholarships(id) ON DELETE CASCADE;


--
-- Name: status_history fk_status_history_actor_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_history
    ADD CONSTRAINT fk_status_history_actor_id_users FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: status_history fk_status_history_application_id_applications; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_history
    ADD CONSTRAINT fk_status_history_application_id_applications FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict PDfWAdQZkgmoN8cLt34YsyEA0IV2SsfaBc8faVdMTpl37HdZeLGwQMRFuXUbwet

