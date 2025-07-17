"use client";
import React, { useState, useRef } from "react";

interface ValidationResult {
    type: string;
    severity: "error" | "warning" | "info";
    lineNumber?: number;
    pairIndex?: number;
    keyName?: string;
    message: string;
    details: string[];
}

const TranslationValidator: React.FC = () => {
    const [originalText, setOriginalText] = useState<string>("");
    const [translatedText, setTranslatedText] = useState<string>("");
    const [validationResults, setValidationResults] = useState<
        ValidationResult[]
    >([]);
    const originalTextareaRef = useRef<HTMLTextAreaElement>(null);
    const translatedTextareaRef = useRef<HTMLTextAreaElement>(null);

    const validateTranslation = (): void => {
        const originalLines = originalText
            .split("\n")
            .filter((line) => line.trim() !== "");
        const translatedLines = translatedText
            .split("\n")
            .filter((line) => line.trim() !== "");
        const results: ValidationResult[] = [];

        // Kiểm tra số lượng dòng
        if (originalLines.length !== translatedLines.length) {
            results.push({
                type: "line-count-mismatch",
                severity: "error",
                message: `Số lượng dòng không khớp`,
                details: [
                    `Bản gốc: ${originalLines.length} dòng`,
                    `Bản dịch: ${translatedLines.length} dòng`,
                    `Chênh lệch: ${
                        originalLines.length - translatedLines.length > 0
                            ? "+"
                            : ""
                    }${originalLines.length - translatedLines.length} dòng`,
                ],
            });
        }

        // Kiểm tra từng cặp key-value
        const maxPairs = Math.floor(
            Math.min(originalLines.length, translatedLines.length) / 2
        );

        for (let pairIndex = 0; pairIndex < maxPairs; pairIndex++) {
            const originalKeyIndex = pairIndex * 2;
            const originalValueIndex = pairIndex * 2 + 1;
            const translatedKeyIndex = pairIndex * 2;
            const translatedValueIndex = pairIndex * 2 + 1;

            const originalKey = originalLines[originalKeyIndex];
            const originalValue = originalLines[originalValueIndex] || "";
            const translatedKey = translatedLines[translatedKeyIndex] || "";
            const translatedValue = translatedLines[translatedValueIndex] || "";

            // 1. Kiểm tra KEY phải giống hệt nhau
            if (originalKey !== translatedKey) {
                results.push({
                    type: "key-mismatch",
                    severity: "error",
                    lineNumber: originalKeyIndex + 1,
                    pairIndex: pairIndex + 1,
                    message: `Key không khớp tại cặp ${pairIndex + 1}`,
                    details: [
                        `Bản gốc (dòng ${
                            originalKeyIndex + 1
                        }): "${originalKey}"`,
                        `Bản dịch (dòng ${
                            translatedKeyIndex + 1
                        }): "${translatedKey}"`,
                        `→ Key phải giống hệt nhau, không được thay đổi`,
                    ],
                });
                continue; // Bỏ qua kiểm tra value nếu key sai
            }

            // 2. Kiểm tra VALUE - HTML tags
            const originalTags = originalValue.match(/<[^>]+>/g) || [];
            const translatedTags = translatedValue.match(/<[^>]+>/g) || [];

            if (originalTags.length !== translatedTags.length) {
                const diff = originalTags.length - translatedTags.length;
                results.push({
                    type: "tag-count-mismatch",
                    severity: "error",
                    lineNumber: originalValueIndex + 1,
                    pairIndex: pairIndex + 1,
                    keyName: originalKey,
                    message: `Số lượng HTML tag không khớp tại "${originalKey}"`,
                    details: [
                        `Bản gốc: ${originalTags.length} tag${
                            originalTags.length > 0
                                ? ` (${originalTags.join(", ")})`
                                : ""
                        }`,
                        `Bản dịch: ${translatedTags.length} tag${
                            translatedTags.length > 0
                                ? ` (${translatedTags.join(", ")})`
                                : ""
                        }`,
                        `→ ${
                            diff > 0
                                ? `Thiếu ${diff} tag`
                                : `Thừa ${Math.abs(diff)} tag`
                        } trong bản dịch`,
                    ],
                });
            } else if (originalTags.join("") !== translatedTags.join("")) {
                results.push({
                    type: "tag-content-mismatch",
                    severity: "warning",
                    lineNumber: originalValueIndex + 1,
                    pairIndex: pairIndex + 1,
                    keyName: originalKey,
                    message: `Nội dung HTML tag không khớp tại "${originalKey}"`,
                    details: [
                        `Bản gốc: ${originalTags.join(", ")}`,
                        `Bản dịch: ${translatedTags.join(", ")}`,
                        `→ Thứ tự hoặc nội dung tag đã thay đổi`,
                    ],
                });
            }

            // 3. Kiểm tra VALUE - Variables
            const originalVars = originalValue.match(/\{[^}]+\}/g) || [];
            const translatedVars = translatedValue.match(/\{[^}]+\}/g) || [];

            if (originalVars.length !== translatedVars.length) {
                const diff = originalVars.length - translatedVars.length;
                results.push({
                    type: "variable-count-mismatch",
                    severity: "error",
                    lineNumber: originalValueIndex + 1,
                    pairIndex: pairIndex + 1,
                    keyName: originalKey,
                    message: `Số lượng biến không khớp tại "${originalKey}"`,
                    details: [
                        `Bản gốc: ${originalVars.length} biến${
                            originalVars.length > 0
                                ? ` (${originalVars.join(", ")})`
                                : ""
                        }`,
                        `Bản dịch: ${translatedVars.length} biến${
                            translatedVars.length > 0
                                ? ` (${translatedVars.join(", ")})`
                                : ""
                        }`,
                        `→ ${
                            diff > 0
                                ? `Thiếu ${diff} biến`
                                : `Thừa ${Math.abs(diff)} biến`
                        } trong bản dịch`,
                    ],
                });
            } else if (originalVars.join("") !== translatedVars.join("")) {
                results.push({
                    type: "variable-content-mismatch",
                    severity: "warning",
                    lineNumber: originalValueIndex + 1,
                    pairIndex: pairIndex + 1,
                    keyName: originalKey,
                    message: `Nội dung biến không khớp tại "${originalKey}"`,
                    details: [
                        `Bản gốc: ${originalVars.join(", ")}`,
                        `Bản dịch: ${translatedVars.join(", ")}`,
                        `→ Tên biến đã thay đổi`,
                    ],
                });
            }

            // 4. Kiểm tra VALUE trống
            if (originalValue.trim() === "" && translatedValue.trim() !== "") {
                results.push({
                    type: "unexpected-content",
                    severity: "warning",
                    lineNumber: originalValueIndex + 1,
                    pairIndex: pairIndex + 1,
                    keyName: originalKey,
                    message: `Bản dịch có nội dung nhưng bản gốc trống tại "${originalKey}"`,
                    details: [
                        `Bản gốc: (trống)`,
                        `Bản dịch: "${translatedValue}"`,
                        `→ Không nên thêm nội dung khi bản gốc trống`,
                    ],
                });
            }

            if (originalValue.trim() !== "" && translatedValue.trim() === "") {
                results.push({
                    type: "missing-content",
                    severity: "error",
                    lineNumber: originalValueIndex + 1,
                    pairIndex: pairIndex + 1,
                    keyName: originalKey,
                    message: `Bản dịch trống nhưng bản gốc có nội dung tại "${originalKey}"`,
                    details: [
                        `Bản gốc: "${originalValue}"`,
                        `Bản dịch: (trống)`,
                        `→ Thiếu nội dung dịch`,
                    ],
                });
            }
        }

        setValidationResults(results);
    };

    const scrollToLine = (lineNumber: number): void => {
        if (originalTextareaRef.current) {
            const textarea = originalTextareaRef.current;
            const targetLine = Math.max(0, lineNumber - 1);
            const scrollTop = targetLine * 20;
            textarea.scrollTop = scrollTop;
            textarea.focus();
        }
        if (translatedTextareaRef.current) {
            const textarea = translatedTextareaRef.current;
            const targetLine = Math.max(0, lineNumber - 1);
            const scrollTop = targetLine * 20;
            textarea.scrollTop = scrollTop;
            textarea.focus();
        }
    };

    const getSeverityColor = (
        severity: "error" | "warning" | "info"
    ): string => {
        switch (severity) {
            case "error":
                return "#ff4d4f";
            case "warning":
                return "#faad14";
            default:
                return "#d48806";
        }
    };

    const getSeverityBadge = (
        severity: "error" | "warning" | "info"
    ): string => {
        switch (severity) {
            case "error":
                return "LỖI";
            case "warning":
                return "CẢNH BÁO";
            default:
                return "THÔNG TIN";
        }
    };

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <div className="bg-white rounded-lg shadow-lg p-6">
                <h1 className="text-2xl font-bold text-gray-800 mb-6">
                    Translation Validator (Key-Value Pairs)
                </h1>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-2">
                            Bản gốc (Tiêu chuẩn)
                        </label>
                        <textarea
                            ref={originalTextareaRef}
                            value={originalText}
                            onChange={(
                                e: React.ChangeEvent<HTMLTextAreaElement>
                            ) => setOriginalText(e.target.value)}
                            className="w-full h-96 p-3 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Ví dụ:
key1
Hello {name}
key2
<b>Welcome</b> to our app"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-2">
                            Bản dịch (Cần kiểm tra)
                        </label>
                        <textarea
                            ref={translatedTextareaRef}
                            value={translatedText}
                            onChange={(
                                e: React.ChangeEvent<HTMLTextAreaElement>
                            ) => setTranslatedText(e.target.value)}
                            className="w-full h-96 p-3 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Ví dụ:
key1
Xin chào {name}
key2
<b>Chào mừng</b> đến với ứng dụng"
                        />
                    </div>
                </div>

                <div className="text-center mb-6">
                    <button
                        onClick={validateTranslation}
                        className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
                    >
                        Kiểm tra bản dịch
                    </button>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                    <h2 className="text-lg font-semibold text-gray-800 mb-4">
                        Kết quả kiểm tra ({validationResults.length} vấn đề)
                    </h2>

                    {validationResults.length === 0 ? (
                        <div className="text-center py-8">
                            <div className="text-green-600 text-lg font-semibold">
                                ✅ Không có lỗi nào được phát hiện
                            </div>
                            <div className="text-gray-600 mt-2">
                                Bản dịch khớp hoàn toàn với bản gốc
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {validationResults.map((result, index) => (
                                <div
                                    key={index}
                                    className="bg-white rounded-lg border-l-4 p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                                    style={{
                                        borderLeftColor: getSeverityColor(
                                            result.severity
                                        ),
                                    }}
                                    onClick={() =>
                                        result.lineNumber &&
                                        scrollToLine(result.lineNumber)
                                    }
                                >
                                    <div className="flex items-start gap-3">
                                        <span
                                            className="px-2 py-1 text-xs font-semibold rounded text-white"
                                            style={{
                                                backgroundColor:
                                                    getSeverityColor(
                                                        result.severity
                                                    ),
                                            }}
                                        >
                                            {getSeverityBadge(result.severity)}
                                        </span>
                                        <div className="flex-1">
                                            <div className="font-semibold text-gray-800 mb-1">
                                                {result.lineNumber &&
                                                    `[Dòng ${result.lineNumber}] `}
                                                {result.message}
                                            </div>
                                            {result.keyName && (
                                                <div className="text-sm text-gray-600 mb-2">
                                                    🔑 Key:{" "}
                                                    <code className="bg-gray-100 px-1 rounded">
                                                        {result.keyName}
                                                    </code>
                                                </div>
                                            )}
                                            <div className="text-sm text-gray-700 space-y-1">
                                                {result.details.map(
                                                    (detail, i) => (
                                                        <div
                                                            key={i}
                                                            className={
                                                                detail.startsWith(
                                                                    "→"
                                                                )
                                                                    ? "text-red-600 font-medium"
                                                                    : ""
                                                            }
                                                        >
                                                            {detail}
                                                        </div>
                                                    )
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TranslationValidator;
