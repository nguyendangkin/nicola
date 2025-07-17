"use client";

import React, { useState, useMemo, useRef } from "react";
import { Input, Button, Space, Typography, Row, Col, Tooltip } from "antd";
import {
    CopyOutlined,
    ClearOutlined,
    EyeOutlined,
    PauseCircleFilled,
    FileExcelFilled,
} from "@ant-design/icons";

const { TextArea } = Input;
const { Title } = Typography;

/* ---------------- Types ---------------- */

type DiffStatus = "same" | "added" | "removed" | "modified" | "tagdiff"; // <-- added

interface DiffWord {
    text: string;
    type: DiffStatus;
}

interface WordDiff {
    original: DiffWord[];
    translated: DiffWord[];
}

interface LineDiff {
    lineNumber: number;
    original: string;
    translated: string;
    status: DiffStatus; // text-level status (added/removed/modified/same)
    tagDiff: boolean; // whether tags differ between original & translated
    tagReport: TagReport | null; // details of tag diff (missing/extra)
    wordDiff: WordDiff | null; // character-level diff for visual
}

interface ChangedLine {
    lineNumber: number;
    index: number;
    status: DiffStatus; // will always be "tagdiff" in QuickNav now
    tagReport: TagReport;
}

/* ---- Tag extraction / comparison helpers ---- */

interface ExtractedTags {
    angle: string[]; // <...>
    curly: string[]; // {...}
    square: string[]; // [...]
}

interface TagReport {
    missing: string[]; // present in original, absent in translated
    extra: string[]; // present in translated, absent in original
    mismatchCounts?: boolean; // convenience flag when counts differ even if tokens text-same (rare)
}

// Global regexes. We capture the full token, including delimiters, so we can do string compare.
const ANGLE_RE = /<[^>]*>/g; // greedy enough; game tags do not nest literal '>'
const CURLY_RE = /\{[^}]*\}/g;
const SQUARE_RE = /\[[^\]]*\]/g;

/** Extract tag-like tokens from a line of text. */
function extractTags(line: string): ExtractedTags {
    const angle = (line.match(/<[^>]+>/g) ?? []).map((tag) =>
        tag.replace(/\(.*?\)/g, "")
    );
    const curly = (line.match(/\{[^}]+}/g) ?? []).map((tag) =>
        tag.replace(/\(.*?\)/g, "")
    );
    const square = (line.match(/\[[^\]]+\]/g) ?? []).map((tag) =>
        tag.replace(/\(.*?\)/g, "")
    );
    return { angle, curly, square };
}

/** Build a multiset map (token -> count). */
function multiset(tokens: string[]): Record<string, number> {
    const map: Record<string, number> = {};
    for (const t of tokens) {
        map[t] = (map[t] || 0) + 1;
    }
    return map;
}

/** Compare original vs translated token arrays, return report. */
function compareTokenSets(orig: string[], trans: string[]): TagReport | null {
    const origMap = multiset(orig);
    const transMap = multiset(trans);
    const missing: string[] = [];
    const extra: string[] = [];
    let mismatchCounts = false;

    // anything in orig missing or count smaller in trans
    for (const tok of Object.keys(origMap)) {
        const o = origMap[tok];
        const t = transMap[tok] ?? 0;
        if (t === 0) {
            missing.push(tok + (o > 1 ? ` x${o}` : ""));
        } else if (t < o) {
            mismatchCounts = true;
            missing.push(tok + ` x${o - t}`);
        }
    }
    // anything in trans not in orig or count larger
    for (const tok of Object.keys(transMap)) {
        const t = transMap[tok];
        const o = origMap[tok] ?? 0;
        if (o === 0) {
            extra.push(tok + (t > 1 ? ` x${t}` : ""));
        } else if (t > o) {
            mismatchCounts = true;
            extra.push(tok + ` x${t - o}`);
        }
    }

    if (missing.length === 0 && extra.length === 0 && !mismatchCounts) {
        return null; // identical
    }
    return { missing, extra, mismatchCounts };
}

/** Compare all 3 tag classes together. */

function compareTags(
    orig: ExtractedTags,
    trans: ExtractedTags
): TagReport | null {
    const repA = compareTokenSets(orig.angle, trans.angle);
    const repC = compareTokenSets(orig.curly, trans.curly);
    const repS = compareTokenSets(orig.square, trans.square);

    const missing: string[] = [];
    const extra: string[] = [];
    let mismatchCounts = false;

    for (const rep of [repA, repC, repS]) {
        if (rep) {
            if (rep.missing.length) missing.push(...rep.missing);
            if (rep.extra.length) extra.push(...rep.extra);
            mismatchCounts = mismatchCounts || !!rep.mismatchCounts;
        }
    }

    if (!missing.length && !extra.length) return null;
    return { missing, extra, mismatchCounts };
}
/* --------------- Component --------------- */

const GameTextComparator: React.FC = () => {
    const [originalText, setOriginalText] = useState("");
    const [translatedText, setTranslatedText] = useState("");
    const [selectedLine, setSelectedLine] = useState<number | null>(null);
    const [copiedLine, setCopiedLine] = useState("");

    const originalRef = useRef<HTMLDivElement>(null);
    const translatedRef = useRef<HTMLDivElement>(null);

    const copyToClipboard = (text: string) => {
        void navigator.clipboard.writeText(text);
    };

    const clearAll = () => {
        setOriginalText("");
        setTranslatedText("");
        setSelectedLine(null);
        setCopiedLine("");
    };

    // Improved character-level diff with word boundaries
    const getImprovedDiff = (
        str1: string,
        str2: string
    ): { original: DiffWord[]; translated: DiffWord[] } => {
        // Convert strings to arrays of characters
        const chars1 = [...str1];
        const chars2 = [...str2];

        // Simple LCS-based diff algorithm
        const lcs = (a: string[], b: string[]): number[][] => {
            const m = a.length;
            const n = b.length;
            const dp: number[][] = Array(m + 1)
                .fill(null)
                .map(() => Array(n + 1).fill(0));

            for (let i = 1; i <= m; i++) {
                for (let j = 1; j <= n; j++) {
                    if (a[i - 1] === b[j - 1]) {
                        dp[i][j] = dp[i - 1][j - 1] + 1;
                    } else {
                        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
                    }
                }
            }
            return dp;
        };

        const dp = lcs(chars1, chars2);
        const result: { original: DiffWord[]; translated: DiffWord[] } = {
            original: [],
            translated: [],
        };

        let i = chars1.length;
        let j = chars2.length;

        const originalParts: { text: string; type: DiffStatus }[] = [];
        const translatedParts: { text: string; type: DiffStatus }[] = [];

        while (i > 0 || j > 0) {
            if (i > 0 && j > 0 && chars1[i - 1] === chars2[j - 1]) {
                originalParts.unshift({ text: chars1[i - 1], type: "same" });
                translatedParts.unshift({ text: chars2[j - 1], type: "same" });
                i--;
                j--;
            } else if (i > 0 && (j === 0 || dp[i - 1][j] >= dp[i][j - 1])) {
                originalParts.unshift({ text: chars1[i - 1], type: "removed" });
                i--;
            } else if (j > 0) {
                translatedParts.unshift({ text: chars2[j - 1], type: "added" });
                j--;
            }
        }

        // Group consecutive characters of the same type
        const groupParts = (
            parts: { text: string; type: DiffStatus }[]
        ): DiffWord[] => {
            if (parts.length === 0) return [];

            const grouped: DiffWord[] = [];
            let current = {
                text: parts[0].text,
                type: parts[0].type,
            } as DiffWord;

            for (let k = 1; k < parts.length; k++) {
                if (parts[k].type === current.type) {
                    current.text += parts[k].text;
                } else {
                    grouped.push(current);
                    current = {
                        text: parts[k].text,
                        type: parts[k].type,
                    } as DiffWord;
                }
            }
            grouped.push(current);
            return grouped;
        };

        // Fill gaps for alignment
        const originalGrouped = groupParts(originalParts);
        const translatedGrouped = groupParts(translatedParts);

        // Create balanced arrays
        const maxLength = Math.max(
            originalGrouped.length,
            translatedGrouped.length
        );

        for (let k = 0; k < maxLength; k++) {
            const origPart = originalGrouped[k] || {
                text: "",
                type: "same" as DiffStatus,
            };
            const transPart = translatedGrouped[k] || {
                text: "",
                type: "same" as DiffStatus,
            };

            result.original.push(origPart);
            result.translated.push(transPart);
        }

        return result;
    };

    // Compute line diffs + tag diffs
    const { diffResult, changedLines } = useMemo((): {
        diffResult: LineDiff[];
        changedLines: ChangedLine[];
    } => {
        const origLines = originalText.split("\n");
        const transLines = translatedText.split("\n");

        const maxLength = Math.max(origLines.length, transLines.length);
        const result: LineDiff[] = [];
        const tagChanged: ChangedLine[] = [];

        for (let i = 0; i < maxLength; i++) {
            const origLine = origLines[i] ?? "";
            const transLine = transLines[i] ?? "";

            // text-level status (kept for main display coloring of Original/Translated panes)
            let status: DiffStatus = "same";
            if (origLine && !transLine) {
                status = "removed";
            } else if (!origLine && transLine) {
                status = "added";
            } else if (origLine !== transLine) {
                status = "modified";
            }

            // Tag comparison (the new important part)
            const tagsOrig = extractTags(origLine);
            const tagsTrans = extractTags(transLine);
            const tagReport = compareTags(tagsOrig, tagsTrans);
            const hasTagDiff = !!tagReport;

            // If tag diff exists, override status in QuickNav semantics.
            const lineData: LineDiff = {
                lineNumber: i + 1,
                original: origLine,
                translated: transLine,
                status,
                tagDiff: hasTagDiff,
                tagReport: tagReport ?? null,
                wordDiff:
                    status === "modified"
                        ? getImprovedDiff(origLine, transLine)
                        : null,
            };

            result.push(lineData);

            if (hasTagDiff) {
                tagChanged.push({
                    lineNumber: i + 1,
                    index: i,
                    status: "tagdiff",
                    tagReport: tagReport!,
                });
            }
        }

        return { diffResult: result, changedLines: tagChanged };
    }, [originalText, translatedText]);

    /** Style per line in the two main panes.
     *  We keep the existing coloring for text diffs BUT overlay purple highlight if tagDiff.
     *  When tagDiff === true, we force purple regardless of status, unless selected.
     */
    const getLineStyle = (
        status: DiffStatus,
        isSelected = false,
        isTagDiff = false,
        isTranslatedPane = false
    ): React.CSSProperties => {
        // base style from prior version
        let baseStyle: React.CSSProperties = {};

        if (isTagDiff) {
            // strong purple flag for dangerous tag mismatch
            baseStyle = {
                backgroundColor: "#f9f0ff", // light purple
                borderLeft: "3px solid #722ed1",
                color: "#531dab",
            };
        } else {
            switch (status) {
                case "added":
                    baseStyle = {
                        backgroundColor: "#e6ffed",
                        borderLeft: "3px solid #52c41a",
                        color: "#389e0d",
                    };
                    break;
                case "removed":
                    baseStyle = {
                        backgroundColor: "#fff2f0",
                        borderLeft: "3px solid #ff4d4f",
                        color: "#cf1322",
                    };
                    break;
                case "modified":
                    baseStyle = {
                        backgroundColor: "#fffbe6",
                        borderLeft: "3px solid #faad14",
                        color: "#d48806",
                    };
                    break;
                default:
                    baseStyle = {
                        backgroundColor: "#fafafa",
                        borderLeft: "3px solid transparent",
                    };
            }
        }

        if (isSelected) {
            return {
                ...baseStyle,
                backgroundColor: "#1890ff",
                color: "white",
                borderLeft: "3px solid #0050b3",
            };
        }

        // Fade visual when a line exists only in the *other* pane (unchanged from your original logic).
        if (!isTagDiff) {
            if (status === (isTranslatedPane ? "removed" : "added")) {
                baseStyle.opacity = 0.3;
            }
        }

        return baseStyle;
    };

    const getWordStyle = (type: DiffStatus): React.CSSProperties => {
        switch (type) {
            case "added":
                return {
                    backgroundColor: "#b7eb8f",
                    color: "#389e0d",
                    padding: "1px 2px",
                    borderRadius: "2px",
                };
            case "removed":
                return {
                    backgroundColor: "#ffaaa0",
                    color: "#cf1322",
                    padding: "1px 2px",
                    borderRadius: "2px",
                };
            case "modified":
                return {
                    backgroundColor: "#ffe58f",
                    color: "#d48806",
                    padding: "1px 2px",
                    borderRadius: "2px",
                };
            case "tagdiff":
                // Should never show per-char tagdiff; included for completeness.
                return {
                    backgroundColor: "#d3adf7",
                    color: "#531dab",
                    padding: "1px 2px",
                    borderRadius: "2px",
                };
            default:
                return {};
        }
    };

    const scrollToLine = (index: number) => {
        setSelectedLine(index);
        const elements = document.querySelectorAll<HTMLElement>(
            `[data-line-index="${index}"]`
        );
        elements.forEach((el) => {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
        });
    };

    const copyOriginalLine = (lineText: string) => {
        setCopiedLine(lineText);
        void navigator.clipboard.writeText(lineText);
    };

    const pasteToTranslated = (lineIndex: number) => {
        if (!copiedLine) return;

        const lines = translatedText.split("\n");
        lines[lineIndex] = copiedLine;
        setTranslatedText(lines.join("\n"));
        setCopiedLine("");
    };

    const renderWords = (words: DiffWord[]) => {
        return words.map((word, index) => (
            <span key={index} style={getWordStyle(word.type)}>
                {word.text}
            </span>
        ));
    };

    const renderTagReportTooltip = (report: TagReport | null): string => {
        if (!report) return "Tags OK";
        const missing = report.missing.length
            ? `Thiếu: ${report.missing.join(", ")}`
            : "";
        const extra = report.extra.length
            ? `Thừa: ${report.extra.join(", ")}`
            : "";
        if (!missing && !extra) return "Tags OK";
        return [missing, extra].filter(Boolean).join(" | ");
    };

    return (
        <div style={{ padding: "20px", maxWidth: "1400px", margin: "0 auto" }}>
            <Title
                level={2}
                style={{ textAlign: "center", marginBottom: "30px" }}
            >
                Game Text Comparator (Tag-Safe)
            </Title>

            <Space
                style={{
                    marginBottom: "20px",
                    width: "100%",
                    justifyContent: "center",
                }}
            >
                <Button
                    type="primary"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(originalText)}
                >
                    Copy Original
                </Button>
                <Button
                    type="primary"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(translatedText)}
                >
                    Copy Translated
                </Button>
                <Button icon={<ClearOutlined />} onClick={clearAll}>
                    Clear All
                </Button>
            </Space>

            {/* Input areas */}
            <Row gutter={16} style={{ marginBottom: "20px" }}>
                <Col span={12}>
                    <div style={{ marginBottom: "8px", fontWeight: "bold" }}>
                        Original Text:
                    </div>
                    <TextArea
                        value={originalText}
                        onChange={(e) => setOriginalText(e.target.value)}
                        placeholder="Paste original game text here..."
                        rows={10}
                        style={{ fontFamily: "monospace", fontSize: "14px" }}
                    />
                </Col>

                <Col span={12}>
                    <div style={{ marginBottom: "8px", fontWeight: "bold" }}>
                        Translated Text:
                    </div>
                    <TextArea
                        value={translatedText}
                        onChange={(e) => setTranslatedText(e.target.value)}
                        placeholder="Paste translated game text here..."
                        rows={10}
                        style={{ fontFamily: "monospace", fontSize: "14px" }}
                    />
                </Col>
            </Row>

            {/* Diff view */}
            {(originalText || translatedText) && (
                <Row gutter={16}>
                    {/* Original Pane */}
                    <Col span={12}>
                        <div
                            style={{ marginBottom: "8px", fontWeight: "bold" }}
                        >
                            Original (Character-Level Diff):
                        </div>
                        <div
                            ref={originalRef}
                            style={{
                                border: "1px solid #d9d9d9",
                                borderRadius: "6px",
                                maxHeight: "400px",
                                overflowY: "auto",
                                backgroundColor: "#fafafa",
                            }}
                        >
                            {diffResult.map((line, index) => (
                                <div
                                    key={index}
                                    data-line-index={index}
                                    onClick={() => setSelectedLine(index)}
                                    onDoubleClick={() => scrollToLine(index)}
                                    style={{
                                        ...getLineStyle(
                                            line.status === "added"
                                                ? "same"
                                                : line.status,
                                            selectedLine === index,
                                            line.tagDiff,
                                            false
                                        ),
                                        padding: "4px 8px",
                                        fontFamily: "monospace",
                                        fontSize: "13px",
                                        borderBottom: "1px solid #f0f0f0",
                                        minHeight: "24px",
                                        display: "flex",
                                        alignItems: "center",
                                        cursor: "pointer",
                                        transition: "all 0.2s ease",
                                    }}
                                >
                                    <span
                                        style={{
                                            color: "#8c8c8c",
                                            width: "30px",
                                            textAlign: "right",
                                            marginRight: "8px",
                                            fontSize: "11px",
                                        }}
                                    >
                                        {line.original ? line.lineNumber : ""}
                                    </span>
                                    <span style={{ flex: 1 }}>
                                        {line.wordDiff
                                            ? renderWords(
                                                  line.wordDiff.original
                                              )
                                            : line.original}
                                    </span>
                                    {line.status !== "same" &&
                                        line.status !== "added" &&
                                        line.original && (
                                            <Tooltip title="Copy this line">
                                                <Button
                                                    type="text"
                                                    size="small"
                                                    icon={<CopyOutlined />}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        copyOriginalLine(
                                                            line.original
                                                        );
                                                    }}
                                                    style={{
                                                        marginLeft: "8px",
                                                    }}
                                                />
                                            </Tooltip>
                                        )}
                                </div>
                            ))}
                        </div>
                    </Col>

                    {/* Translated Pane */}
                    <Col span={12}>
                        <div
                            style={{ marginBottom: "8px", fontWeight: "bold" }}
                        >
                            Translated (Character-Level Diff):
                        </div>
                        <div
                            ref={translatedRef}
                            style={{
                                border: "1px solid #d9d9d9",
                                borderRadius: "6px",
                                maxHeight: "400px",
                                overflowY: "auto",
                                backgroundColor: "#fafafa",
                            }}
                        >
                            {diffResult.map((line, index) => (
                                <div
                                    key={index}
                                    data-line-index={index}
                                    onClick={() => setSelectedLine(index)}
                                    onDoubleClick={() => scrollToLine(index)}
                                    style={{
                                        ...getLineStyle(
                                            line.status === "removed"
                                                ? "same"
                                                : line.status,
                                            selectedLine === index,
                                            line.tagDiff,
                                            true
                                        ),
                                        padding: "4px 8px",
                                        fontFamily: "monospace",
                                        fontSize: "13px",
                                        borderBottom: "1px solid #f0f0f0",
                                        minHeight: "24px",
                                        display: "flex",
                                        alignItems: "center",
                                        cursor: "pointer",
                                        transition: "all 0.2s ease",
                                    }}
                                >
                                    <span
                                        style={{
                                            color: "#8c8c8c",
                                            width: "30px",
                                            textAlign: "right",
                                            marginRight: "8px",
                                            fontSize: "11px",
                                        }}
                                    >
                                        {line.translated ? line.lineNumber : ""}
                                    </span>
                                    <span style={{ flex: 1 }}>
                                        {line.wordDiff
                                            ? renderWords(
                                                  line.wordDiff.translated
                                              )
                                            : line.translated}
                                    </span>
                                    {line.status !== "same" &&
                                        line.status !== "removed" &&
                                        copiedLine && (
                                            <Tooltip title="Paste copied line here">
                                                <Button
                                                    type="text"
                                                    size="small"
                                                    icon={<FileExcelFilled />}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        pasteToTranslated(
                                                            index
                                                        );
                                                    }}
                                                    style={{
                                                        marginLeft: "8px",
                                                        color: "#52c41a",
                                                    }}
                                                />
                                            </Tooltip>
                                        )}
                                </div>
                            ))}
                        </div>
                    </Col>
                </Row>
            )}

            {/* Quick Navigation - now ONLY tag-diff lines */}
            {changedLines.length > 0 && (
                <div
                    style={{
                        marginTop: "20px",
                        marginBottom: "20px",
                        padding: "10px",
                        backgroundColor: "#f0e7ff",
                        borderRadius: "6px",
                        border: "1px solid #d3adf7",
                    }}
                >
                    <strong>
                        Quick Navigation (⚠ Tag mismatches:{" "}
                        {changedLines.length}):
                    </strong>
                    <div style={{ marginTop: "8px" }}>
                        {changedLines.map((line, index) => (
                            <Tooltip
                                key={index}
                                title={renderTagReportTooltip(line.tagReport)}
                            >
                                <Button
                                    size="small"
                                    style={{
                                        marginRight: "4px",
                                        marginBottom: "4px",
                                        backgroundColor: "#722ed1",
                                        borderColor: "#722ed1",
                                        color: "#fff",
                                    }}
                                    onClick={() => scrollToLine(line.index)}
                                    icon={<EyeOutlined />}
                                >
                                    Line {line.lineNumber}
                                </Button>
                            </Tooltip>
                        ))}
                    </div>
                </div>
            )}

            {/* Legend */}
            {(originalText || translatedText) && (
                <div
                    style={{
                        marginTop: "20px",
                        padding: "10px",
                        backgroundColor: "#f9f9f9",
                        borderRadius: "6px",
                        fontSize: "12px",
                    }}
                >
                    <strong>Legend:</strong>
                    <span style={{ color: "#722ed1", marginLeft: "10px" }}>
                        ● Tag mismatch (PURPLE)
                    </span>
                    <span style={{ color: "#52c41a", marginLeft: "10px" }}>
                        ● Added (text only)
                    </span>
                    <span style={{ color: "#ff4d4f", marginLeft: "10px" }}>
                        ● Removed (text only)
                    </span>
                    <span style={{ color: "#faad14", marginLeft: "10px" }}>
                        ● Modified (text only)
                    </span>
                    <span style={{ color: "#8c8c8c", marginLeft: "10px" }}>
                        ● Same
                    </span>
                    <span style={{ color: "#1890ff", marginLeft: "10px" }}>
                        ● Selected
                    </span>
                    <div style={{ marginTop: "5px" }}>
                        💡 <strong>Tip:</strong> Chỉ những dòng sai tag mới hiện
                        ở Quick Navigation. Dịch sai tag có thể làm crash game!
                    </div>
                </div>
            )}
        </div>
    );
};

export default GameTextComparator;
