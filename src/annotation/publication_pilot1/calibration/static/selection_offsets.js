(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.SelectionOffsets = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function codePointOffsetFromUtf16(text, utf16Offset) {
    if (!Number.isInteger(utf16Offset) || utf16Offset < 0 || utf16Offset > text.length) throw new Error("UTF16_OFFSET_OUT_OF_RANGE");
    if (utf16Offset > 0 && utf16Offset < text.length) {
      const previous = text.charCodeAt(utf16Offset - 1), current = text.charCodeAt(utf16Offset);
      if (previous >= 0xd800 && previous <= 0xdbff && current >= 0xdc00 && current <= 0xdfff) throw new Error("UTF16_OFFSET_SPLITS_SURROGATE_PAIR");
    }
    return Array.from(text.slice(0, utf16Offset)).length;
  }

  function utf16OffsetFromCodePoint(text, codePointOffset) {
    const points = Array.from(text);
    if (!Number.isInteger(codePointOffset) || codePointOffset < 0 || codePointOffset > points.length) throw new Error("CODEPOINT_OFFSET_OUT_OF_RANGE");
    return points.slice(0, codePointOffset).join("").length;
  }

  function sliceByCodePoints(text, start, end) { return Array.from(text).slice(start, end).join(""); }

  function selectionToCodePointOffsets(container, selection) {
    if (!selection || selection.rangeCount !== 1 || selection.isCollapsed) throw new Error("NON_EMPTY_SELECTION_REQUIRED");
    const selected = selection.getRangeAt(0);
    if (!container.contains(selected.startContainer) || !container.contains(selected.endContainer)) throw new Error("SELECTION_OUTSIDE_SOURCE_TEXT");
    const prefix = document.createRange(); prefix.selectNodeContents(container); prefix.setEnd(selected.startContainer, selected.startOffset);
    const through = document.createRange(); through.selectNodeContents(container); through.setEnd(selected.endContainer, selected.endOffset);
    const startOffset = Array.from(prefix.toString()).length, endOffset = Array.from(through.toString()).length;
    const exactText = sliceByCodePoints(container.textContent, startOffset, endOffset);
    if (exactText !== selected.toString()) throw new Error("SELECTION_ROUND_TRIP_MISMATCH");
    return { startOffset, endOffset, exactText };
  }

  return { codePointOffsetFromUtf16, utf16OffsetFromCodePoint, sliceByCodePoints, selectionToCodePointOffsets };
});

