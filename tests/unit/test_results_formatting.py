import sys
from decimal import Decimal

import pandas as pd
from PyQt6.QtWidgets import QApplication

from localsql_explorer.ui.results_view import PandasTableModel


app = QApplication.instance() or QApplication(sys.argv)


def get_display_value(model, row=0, column=0):
    index = model.index(row, column)
    return model.data(index)


def test_float_precision_preserved():
    df = pd.DataFrame({"value": [123.456789, 0.000123456, 1000.0]})
    model = PandasTableModel(df)

    values = [get_display_value(model, i, 0) for i in range(len(df))]

    assert values[0] == "123.456789"
    assert values[1] == "0.000123456"
    assert values[2] == "1000"


def test_decimal_preserves_scale():
    df = pd.DataFrame({"amount": [Decimal("123.450"), Decimal("0.3000")]})
    model = PandasTableModel(df)

    values = [get_display_value(model, i, 0) for i in range(len(df))]

    assert values[0] == "123.450"
    assert values[1] == "0.3000"