from __future__ import annotations

from decimal import Decimal

from app.models.domain import InstrumentAnalysis


def price_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def format_pine_data(analysis: InstrumentAnalysis) -> str:
    upper = ",".join(price_text(level.strike_price) for level in analysis.upper_levels)
    lower = ",".join(price_text(level.strike_price) for level in analysis.lower_levels)
    return f"{analysis.instrument.symbol} | {upper} | {lower}"


PINE_SCRIPT = r'''//@version=5
indicator("NSE Opening-Price OI Levels", overlay=true, max_lines_count=50, max_labels_count=50)

box1 = input.string("", "OI Data (Box 1)", group="NSE OI Levels", tooltip="SYMBOL | resistance levels | support levels")
box2 = input.string("", "OI Data (Box 2)", group="NSE OI Levels", tooltip="Add a second symbol line if needed")
showLabels = input.bool(true, "Show price labels", group="NSE OI Levels")

var line[] drawnLines = array.new_line()
var label[] drawnLabels = array.new_label()

clearDrawings() =>
    if array.size(drawnLines) > 0
        for i = 0 to array.size(drawnLines) - 1
            line.delete(array.get(drawnLines, i))
        array.clear(drawnLines)
    if array.size(drawnLabels) > 0
        for i = 0 to array.size(drawnLabels) - 1
            label.delete(array.get(drawnLabels, i))
        array.clear(drawnLabels)

cleanTicker = str.upper(str.replace_all(syminfo.ticker, "NSE:", ""))
matched = ""
for raw in array.from(box1, box2)
    pieces = str.split(raw, "|")
    if array.size(pieces) == 3
        candidate = str.upper(str.trim(array.get(pieces, 0)))
        if candidate == cleanTicker
            matched := raw

if barstate.islast
    clearDrawings()
    pieces = str.split(matched, "|")
    if array.size(pieces) == 3
        upper = str.split(str.trim(array.get(pieces, 1)), ",")
        lower = str.split(str.trim(array.get(pieces, 2)), ",")
        if array.size(upper) > 0
            for i = 0 to array.size(upper) - 1
                value = str.tonumber(str.trim(array.get(upper, i)))
                if not na(value)
                    array.push(drawnLines, line.new(bar_index, value, bar_index + 1, value, extend=extend.right, color=color.new(color.green, 0), style=line.style_dashed, width=2))
                    if showLabels
                        array.push(drawnLabels, label.new(bar_index, value, "R" + str.tostring(i + 1) + ": ₹" + str.tostring(value), xloc=xloc.bar_index, style=label.style_label_left, textcolor=color.white, color=color.new(color.green, 20)))
        if array.size(lower) > 0
            for i = 0 to array.size(lower) - 1
                value = str.tonumber(str.trim(array.get(lower, i)))
                if not na(value)
                    array.push(drawnLines, line.new(bar_index, value, bar_index + 1, value, extend=extend.right, color=color.new(color.red, 0), style=line.style_dashed, width=2))
                    if showLabels
                        array.push(drawnLabels, label.new(bar_index, value, "S" + str.tostring(i + 1) + ": ₹" + str.tostring(value), xloc=xloc.bar_index, style=label.style_label_left, textcolor=color.white, color=color.new(color.red, 20)))
'''
