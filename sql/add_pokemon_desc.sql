-- 为 pokemon 表新增宠物描述字段
ALTER TABLE public.pokemon
ADD COLUMN IF NOT EXISTS "desc" TEXT NOT NULL DEFAULT '';

COMMENT ON COLUMN public.pokemon."desc" IS '宠物描述（来自官方 base_info 接口的 desc 字段）';
