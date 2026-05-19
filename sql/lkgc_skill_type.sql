/*
 Navicat Premium Dump SQL

 Source Server         : 腾讯云新
 Source Server Type    : PostgreSQL
 Source Server Version : 180003 (180003)
 Source Host           : 159.75.222.113:5432
 Source Catalog        : wikiroco
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 180003 (180003)
 File Encoding         : 65001

 Date: 19/05/2026 14:01:40
*/


-- ----------------------------
-- Table structure for lkgc_skill_type
-- ----------------------------
DROP TABLE IF EXISTS "public"."lkgc_skill_type";
CREATE TABLE "public"."lkgc_skill_type" (
  "id" int8 NOT NULL DEFAULT nextval('your_table_name_id_seq'::regclass),
  "name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "category_id" int4,
  "damage_id" int4
)
;

-- ----------------------------
-- Records of lkgc_skill_type
-- ----------------------------
INSERT INTO "public"."lkgc_skill_type" VALUES (1, '物攻', 1, 1);
INSERT INTO "public"."lkgc_skill_type" VALUES (2, '魔攻', 1, 2);
INSERT INTO "public"."lkgc_skill_type" VALUES (3, '状态', 3, -1);
INSERT INTO "public"."lkgc_skill_type" VALUES (4, '防御', 2, -1);

-- ----------------------------
-- Primary Key structure for table lkgc_skill_type
-- ----------------------------
ALTER TABLE "public"."lkgc_skill_type" ADD CONSTRAINT "your_table_name_pkey" PRIMARY KEY ("id");
