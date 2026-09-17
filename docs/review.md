# Review workflow

AI output is immutable in `ai_results`. A reviewer writes final values only to `meter_readings`; every changed field becomes a `manual_corrections` row and each confirmation/rejection is audited. Corrected values never overwrite AI values.
