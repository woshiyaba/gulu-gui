ALTER TABLE public.egg_hatch_pet
ADD COLUMN big_size_length_min int4 NOT NULL DEFAULT 0,
ADD COLUMN big_size_weight_min int4 NOT NULL DEFAULT 0,
ADD COLUMN small_size_length_max int4 NOT NULL DEFAULT 0,
ADD COLUMN small_size_weight_max int4 NOT NULL DEFAULT 0;