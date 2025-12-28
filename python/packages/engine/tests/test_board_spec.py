from monopoly_engine.board import (
    BOARD_SPEC,
    PROPERTY_RENT_TABLES,
    RAILROAD_RENTS,
    TAX_AMOUNTS,
    UTILITY_RENT_MULTIPLIER,
)


def test_board_spec_has_40_spaces_with_contiguous_indexes() -> None:
    assert len(BOARD_SPEC) == 40
    indexes = [index for index, _, _, _, _ in BOARD_SPEC]
    assert indexes == list(range(40))


def test_board_rent_and_tax_tables_match_expected_invariants() -> None:
    assert RAILROAD_RENTS == [25, 50, 100, 200]
    assert UTILITY_RENT_MULTIPLIER == {1: 4, 2: 10}
    assert TAX_AMOUNTS == {4: 200, 38: 100}

    assert PROPERTY_RENT_TABLES[1] == [2, 10, 30, 90, 160, 250]
    assert PROPERTY_RENT_TABLES[39] == [50, 200, 600, 1400, 1700, 2000]

