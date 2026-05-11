# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A6: SimLogger row-based rotation produces suffixed archive files."""

import os
from npc_sim.diagnostics.sim_logger import SimLogger


def test_rotate_archives_have_suffixed_names(tmp_path):
    logger = SimLogger(log_dir=str(tmp_path), rotate_every_rows=3)
    for _ in range(7):
        logger._row_count += 1
        if logger._row_count % logger._rotate_every_rows == 0:
            logger._rotate()
    logger.close()
    files = sorted(os.listdir(tmp_path))
    assert "sim_full.csv" in files
    assert "sim_full.0001.csv" in files
    assert "sim_full.0002.csv" in files
    assert "sim_full.0003.csv" not in files


def test_active_file_keeps_canonical_name(tmp_path):
    logger = SimLogger(log_dir=str(tmp_path), rotate_every_rows=2)
    assert logger.log_path.endswith("sim_full.csv")
    logger._row_count = 2
    logger._rotate()
    assert logger.log_path.endswith("sim_full.csv")
    logger.close()
    assert os.path.exists(os.path.join(tmp_path, "sim_full.0001.csv"))
    assert os.path.exists(os.path.join(tmp_path, "sim_full.csv"))


def test_disabled_logger_skips_rotation(tmp_path):
    logger = SimLogger(log_dir=str(tmp_path), enabled=False, rotate_every_rows=1)
    logger._row_count = 100
    logger._rotate()
    assert not os.path.exists(os.path.join(tmp_path, "sim_full.0001.csv"))


def test_default_rotate_threshold_is_one_million():
    logger = SimLogger(enabled=False)
    assert logger._rotate_every_rows == 1_000_000
