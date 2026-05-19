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

 Date: 19/05/2026 14:01:53
*/


-- ----------------------------
-- Table structure for attribute
-- ----------------------------
DROP TABLE IF EXISTS "public"."attribute";
CREATE TABLE "public"."attribute" (
  "id" int4 NOT NULL DEFAULT nextval('attribute_id_seq'::regclass),
  "name" varchar(10) COLLATE "pg_catalog"."default" NOT NULL,
  "sort_order" int4 NOT NULL DEFAULT 0,
  "image" varchar(255) COLLATE "pg_catalog"."default" NOT NULL DEFAULT ''::character varying,
  "lkgc_id" int4
)
;
COMMENT ON COLUMN "public"."attribute"."lkgc_id" IS '对应洛克广场的技能属性id';

-- ----------------------------
-- Records of attribute
-- ----------------------------
INSERT INTO "public"."attribute" VALUES (8, '地', 8, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/251910c661124df195655cfca5d39c3b.webp', 18);
INSERT INTO "public"."attribute" VALUES (1, '火', 1, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/59e06a7a5b9d449d881c825397d03896.webp', 9);
INSERT INTO "public"."attribute" VALUES (2, '水', 2, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/17fbac3f4d0c4ec4ade39a4ad0db4677.webp', 10);
INSERT INTO "public"."attribute" VALUES (3, '草', 3, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/aa84dd993913477e955f3f96169eeb5d.webp', 4);
INSERT INTO "public"."attribute" VALUES (7, '普通', 7, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/d04106b1ae3c46f791bcd4ddfbbd4100.webp', 5);
INSERT INTO "public"."attribute" VALUES (4, '光', 4, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/242ac24ea8d34fa3b18cb9ecd6b258f2.webp', 6);
INSERT INTO "public"."attribute" VALUES (5, '恶', 5, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/2b98cdd9c96b4fd294756f571c13b624.webp', 1);
INSERT INTO "public"."attribute" VALUES (15, '翼', 15, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/d230f3bee6e340fcba8bba9c10628e04.webp', 2);
INSERT INTO "public"."attribute" VALUES (6, '幽', 6, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/fdad7497e51f4cdd971aa3a5d41ee70b.webp', 3);
INSERT INTO "public"."attribute" VALUES (12, '毒', 12, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/f6e870f52a6d41c7a55ca84e0b538243.webp', 7);
INSERT INTO "public"."attribute" VALUES (13, '虫', 13, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/7f9f9ff8fea44b4b8e545fe6c988c486.webp', 8);
INSERT INTO "public"."attribute" VALUES (9, '冰', 9, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/c085b44f9d904705a33ed661f80cc48c.webp', 11);
INSERT INTO "public"."attribute" VALUES (11, '电', 11, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/f8b2019340f648be9c206087ec83bc8e.webp', 12);
INSERT INTO "public"."attribute" VALUES (18, '幻', 18, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/a92d8d4091cc401d9283d2a46fbea3b7.webp', 13);
INSERT INTO "public"."attribute" VALUES (17, '机械', 17, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/b0f28f4f4dfc4b609e91882ff5e7d6cf.webp', 14);
INSERT INTO "public"."attribute" VALUES (10, '龙', 10, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/07e60b9564aa48f1a1ccd0c0545421d7.webp', 15);
INSERT INTO "public"."attribute" VALUES (16, '萌', 16, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/abe52acf1b4f4325a7f6642ec85192f2.webp', 16);
INSERT INTO "public"."attribute" VALUES (14, '武', 14, 'https://wikiroco-1309114022.cos.ap-guangzhou.myqcloud.com/attribute/image/d0b6fa046859415291dfd292066f4bdd.webp', 17);

-- ----------------------------
-- Uniques structure for table attribute
-- ----------------------------
ALTER TABLE "public"."attribute" ADD CONSTRAINT "uk_attribute_name" UNIQUE ("name");
ALTER TABLE "public"."attribute" ADD CONSTRAINT "uk_attribute_sort" UNIQUE ("sort_order");

-- ----------------------------
-- Primary Key structure for table attribute
-- ----------------------------
ALTER TABLE "public"."attribute" ADD CONSTRAINT "attribute_pkey" PRIMARY KEY ("id");
