"""Create the sample workbook used for Excel assistant demos."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook


def main() -> None:
    output = Path("inputs/sample_sales.xlsx")
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sales"
    sheet.append(["Region", "Product", "Units", "Unit Price"])
    for row in [
        ["North", "Widget", 12, 10.0],
        ["South", "Widget", 18, 10.0],
        ["East", "Gadget", 9, 25.0],
        ["West", "Gadget", 22, 25.0],
        ["North", "Gadget", 7, 25.0],
        ["South", "Widget", 15, 10.0],
    ]:
        sheet.append(row)
    workbook.save(output)
    print(output)


if __name__ == "__main__":
    main()
