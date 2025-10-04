-- Исправление таблицы transactions
-- Добавляем недостающую колонку 'type'

-- Проверяем, существует ли колонка 'type'
DO $$
BEGIN
    -- Добавляем колонку 'type' если её нет
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'type'
    ) THEN
        ALTER TABLE transactions ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'spend';
        RAISE NOTICE 'Колонка type добавлена в таблицу transactions';
    ELSE
        RAISE NOTICE 'Колонка type уже существует в таблице transactions';
    END IF;
END $$;

-- Обновляем существующие записи
UPDATE transactions 
SET type = 'spend' 
WHERE type IS NULL OR type = '';

-- Проверяем результат
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'transactions' 
ORDER BY ordinal_position;
