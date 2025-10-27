-- Index untuk partner_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_po_partner_id'
    ) THEN
        CREATE INDEX idx_po_partner_id ON purchase_order (partner_id);
    END IF;
END
$$;

-- Index untuk state
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_po_state'
    ) THEN
        CREATE INDEX idx_po_state ON purchase_order (state);
    END IF;
END
$$;

-- Index untuk received_leadtime
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_po_received_leadtime'
    ) THEN
        CREATE INDEX idx_po_received_leadtime ON purchase_order (received_leadtime);
    END IF;
END
$$;