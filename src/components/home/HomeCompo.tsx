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

type DiffStatus = "same" | "added" | "removed" | "modified";

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
    status: DiffStatus;
    wordDiff: WordDiff | null;
}

interface ChangedLine {
    lineNumber: number;
    index: number;
    status: DiffStatus;
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

    // Word-level diff
    const getWordDiff = (original: string, translated: string): WordDiff => {
        const origWords = original.split(/(\s+)/);
        const transWords = translated.split(/(\s+)/);

        const maxLength = Math.max(origWords.length, transWords.length);
        const result: WordDiff = { original: [], translated: [] };

        for (let i = 0; i < maxLength; i++) {
            const origWord = origWords[i] ?? "";
            const transWord = transWords[i] ?? "";

            if (origWord === transWord) {
                result.original.push({ text: origWord, type: "same" });
                result.translated.push({ text: transWord, type: "same" });
            } else if (origWord && !transWord) {
                result.original.push({ text: origWord, type: "removed" });
                result.translated.push({ text: "", type: "removed" });
            } else if (!origWord && transWord) {
                result.original.push({ text: "", type: "added" });
                result.translated.push({ text: transWord, type: "added" });
            } else {
                result.original.push({ text: origWord, type: "modified" });
                result.translated.push({ text: transWord, type: "modified" });
            }
        }

        return result;
    };

    // Tách thành các dòng để so sánh
    const { diffResult, changedLines } = useMemo((): {
        diffResult: LineDiff[];
        changedLines: ChangedLine[];
    } => {
        const origLines = originalText.split("\n");
        const transLines = translatedText.split("\n");

        const maxLength = Math.max(origLines.length, transLines.length);
        const result: LineDiff[] = [];
        const changed: ChangedLine[] = [];

        for (let i = 0; i < maxLength; i++) {
            const origLine = origLines[i] ?? "";
            const transLine = transLines[i] ?? "";

            let status: DiffStatus = "same";
            if (origLine && !transLine) {
                status = "removed";
            } else if (!origLine && transLine) {
                status = "added";
            } else if (origLine !== transLine) {
                status = "modified";
            }

            const lineData: LineDiff = {
                lineNumber: i + 1,
                original: origLine,
                translated: transLine,
                status,
                wordDiff:
                    status === "modified"
                        ? getWordDiff(origLine, transLine)
                        : null,
            };

            result.push(lineData);

            if (status !== "same") {
                changed.push({ lineNumber: i + 1, index: i, status });
            }
        }

        return { diffResult: result, changedLines: changed };
    }, [originalText, translatedText]);

    const getLineStyle = (
        status: DiffStatus,
        isSelected = false
    ): React.CSSProperties => {
        let baseStyle: React.CSSProperties = {};

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

        if (isSelected) {
            return {
                ...baseStyle,
                backgroundColor: "#1890ff",
                color: "white",
                borderLeft: "3px solid #0050b3",
            };
        }

        return baseStyle;
    };

    const getWordStyle = (type: DiffStatus): React.CSSProperties => {
        switch (type) {
            case "added":
                return {
                    backgroundColor: "#b7eb8f",
                    color: "#389e0d",
                    padding: "2px 4px",
                    borderRadius: "3px",
                };
            case "removed":
                return {
                    backgroundColor: "#ffaaa0",
                    color: "#cf1322",
                    padding: "2px 4px",
                    borderRadius: "3px",
                };
            case "modified":
                return {
                    backgroundColor: "#ffe58f",
                    color: "#d48806",
                    padding: "2px 4px",
                    borderRadius: "3px",
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
        // Nếu muốn dán nhiều lần, comment dòng dưới:
        setCopiedLine("");
    };

    const renderWords = (words: DiffWord[]) => {
        return words.map((word, index) => (
            <span key={index} style={getWordStyle(word.type)}>
                {word.text}
            </span>
        ));
    };

    return (
        <div style={{ padding: "20px", maxWidth: "1400px", margin: "0 auto" }}>
            <Title
                level={2}
                style={{ textAlign: "center", marginBottom: "30px" }}
            >
                Game Text Comparator
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
                    <Col span={12}>
                        <div
                            style={{ marginBottom: "8px", fontWeight: "bold" }}
                        >
                            Original (Diff View):
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
                                            selectedLine === index
                                        ),
                                        padding: "4px 8px",
                                        fontFamily: "monospace",
                                        fontSize: "13px",
                                        borderBottom: "1px solid #f0f0f0",
                                        minHeight: "24px",
                                        display: "flex",
                                        alignItems: "center",
                                        opacity:
                                            line.status === "added" ? 0.3 : 1,
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

                    <Col span={12}>
                        <div
                            style={{ marginBottom: "8px", fontWeight: "bold" }}
                        >
                            Translated (Diff View):
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
                                            selectedLine === index
                                        ),
                                        padding: "4px 8px",
                                        fontFamily: "monospace",
                                        fontSize: "13px",
                                        borderBottom: "1px solid #f0f0f0",
                                        minHeight: "24px",
                                        display: "flex",
                                        alignItems: "center",
                                        opacity:
                                            line.status === "removed" ? 0.3 : 1,
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

            {/* Quick Navigation */}
            {changedLines.length > 0 && (
                <div
                    style={{
                        marginTop: "20px",
                        marginBottom: "20px",
                        padding: "10px",
                        backgroundColor: "#f6ffed",
                        borderRadius: "6px",
                        border: "1px solid #b7eb8f",
                    }}
                >
                    <strong>
                        Quick Navigation ({changedLines.length} differences):
                    </strong>
                    <div style={{ marginTop: "8px" }}>
                        {changedLines.map((line, index) => (
                            <Button
                                key={index}
                                size="small"
                                type={
                                    line.status === "modified"
                                        ? "primary"
                                        : "default"
                                }
                                danger={line.status === "removed"}
                                style={{
                                    marginRight: "4px",
                                    marginBottom: "4px",
                                }}
                                onClick={() => scrollToLine(line.index)}
                                icon={<EyeOutlined />}
                            >
                                Line {line.lineNumber}
                            </Button>
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
                    <span style={{ color: "#52c41a", marginLeft: "10px" }}>
                        ● Added
                    </span>
                    <span style={{ color: "#ff4d4f", marginLeft: "10px" }}>
                        ● Removed
                    </span>
                    <span style={{ color: "#faad14", marginLeft: "10px" }}>
                        ● Modified
                    </span>
                    <span style={{ color: "#8c8c8c", marginLeft: "10px" }}>
                        ● Same
                    </span>
                    <span style={{ color: "#1890ff", marginLeft: "10px" }}>
                        ● Selected
                    </span>
                    <div style={{ marginTop: "5px" }}>
                        💡 <strong>Tips:</strong> Click line numbers to jump •
                        Copy from original • Paste to translated • Word-level
                        highlighting
                    </div>
                </div>
            )}
        </div>
    );
};

export default GameTextComparator;
