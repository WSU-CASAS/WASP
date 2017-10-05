
CREATE TABLE annotation(
    aid integer NOT NULL, 
    name text NOT NULL);

CREATE SEQUENCE annotation_aid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE annotation_aid_seq OWNED BY annotation.aid;
ALTER TABLE annotation ALTER COLUMN aid SET DEFAULT nextval('annotation_aid_seq'::regclass);
ALTER TABLE ONLY annotation ADD CONSTRAINT annotation_pkey PRIMARY KEY (aid);
ALTER TABLE ONLY annotation ADD CONSTRAINT annotation_name_key UNIQUE (name);

CREATE TABLE chromosome(
    cid integer NOT NULL, 
    genome text NOT NULL,  
    accuracy numeric NOT NULL DEFAULT -1);

CREATE SEQUENCE chromosome_cid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE chromosome_cid_seq OWNED BY chromosome.cid;
ALTER TABLE chromosome ALTER COLUMN cid SET DEFAULT nextval('chromosome_cid_seq'::regclass);
ALTER TABLE ONLY chromosome ADD CONSTRAINT chromosome_pkey PRIMARY KEY (cid);
ALTER TABLE ONLY chromosome ADD CONSTRAINT chromosome_genome_key UNIQUE (genome);

CREATE TABLE manager(
    mid integer NOT NULL,
    dir_work text NOT NULL,
    dir_data text NOT NULL,
    dir_orig text NOT NULL,
    site_config text NOT NULL,
    population integer NOT NULL,
    crossover integer NOT NULL,
    mutation_rate real NOT NULL,
    survival_rate real NOT NULL,
    reproduction_rate real NOT NULL,
    seed_size real NOT NULL,
    max_generation integer NOT NULL);

CREATE SEQUENCE manager_mid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE manager_mid_seq OWNED BY manager.mid;
ALTER TABLE manager ALTER COLUMN mid SET DEFAULT nextval('manager_mid_seq'::regclass);
ALTER TABLE ONLY manager ADD CONSTRAINT manager_pkey PRIMARY KEY (mid);

CREATE TABLE generation(
    gid integer NOT NULL);

CREATE SEQUENCE generation_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE generation_gid_seq OWNED BY generation.gid;
ALTER TABLE generation ALTER COLUMN gid SET DEFAULT nextval('generation_gid_seq'::regclass);
ALTER TABLE ONLY generation ADD CONSTRAINT generation_pkey PRIMARY KEY (gid);

CREATE TABLE chrom_ann(
    cid integer NOT NULL, 
    aid integer NOT NULL, 
    tp integer NOT NULL, 
    fp integer NOT NULL, 
    tn integer NOT NULL, 
    fn integer NOT NULL);

ALTER TABLE ONLY chrom_ann ADD CONSTRAINT chrom_ann_pkey PRIMARY KEY (cid, aid);
ALTER TABLE ONLY chrom_ann ADD CONSTRAINT chrom_ann_cid_fkey FOREIGN KEY (cid) REFERENCES chromosome(cid) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY chrom_ann ADD CONSTRAINT chrom_ann_aid_fkey FOREIGN KEY (aid) REFERENCES annotation(aid) ON UPDATE CASCADE ON DELETE CASCADE;

CREATE TABLE chrom_gen(
    cid integer NOT NULL, 
    gid integer NOT NULL, 
    mid integer NOT NULL, 
    final_fitness numeric);

ALTER TABLE ONLY chrom_gen ADD CONSTRAINT chrom_gen_pkey PRIMARY KEY (cid, gid, mid);
ALTER TABLE ONLY chrom_gen ADD CONSTRAINT chrom_gen_cid_fkey FOREIGN KEY (cid) REFERENCES chromosome(cid) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY chrom_gen ADD CONSTRAINT chrom_gen_gid_fkey FOREIGN KEY (gid) REFERENCES generation(gid) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY chrom_gen ADD CONSTRAINT chrom_gen_mid_fkey FOREIGN KEY (mid) REFERENCES manager(mid) ON UPDATE CASCADE ON DELETE CASCADE;

CREATE INDEX genome_index ON chromosome USING btree (genome);
CREATE INDEX manager_index ON chrom_gen USING btree (mid);



