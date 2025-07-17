import React, { useState } from "react";

const GameTranslationChecker = () => {
    const [originalText, setOriginalText] = useState("");
    const [translatedText, setTranslatedText] = useState("");
    const [comparisonResult, setComparisonResult] = useState(null);

    // Xử lý khi file được thả vào textarea
    const handleDrop = (e, setText) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                setText(event.target.result);
            };
            reader.readAsText(file);
        }
    };

    // Ngăn chặn hành vi mặc định khi kéo file vào
    const handleDragOver = (e) => {
        e.preventDefault();
    };

    const parseGameFile = (content) => {
        const lines = content.split("\n");
        const entries = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith("SelfId=")) {
                const selfId = line.substring(7);
                let textLine = "";

                for (let j = i + 1; j < lines.length; j++) {
                    if (lines[j].trim().startsWith("Text=")) {
                        textLine = lines[j].trim().substring(5);
                        break;
                    }
                    if (lines[j].trim().startsWith("SelfId=")) {
                        break;
                    }
                }

                entries.push({
                    selfId,
                    text: textLine,
                    lineNumber: i + 1,
                });
            }
        }

        return entries;
    };

    const compareFiles = () => {
        try {
            const originalEntries = parseGameFile(originalText);
            const translatedEntries = parseGameFile(translatedText);

            const issues = [];
            const changes = [];

            const originalIds = new Set(originalEntries.map((e) => e.selfId));
            const translatedIds = new Set(
                translatedEntries.map((e) => e.selfId)
            );

            // Find missing SelfIds
            for (const id of originalIds) {
                if (!translatedIds.has(id)) {
                    issues.push({
                        type: "missing",
                        selfId: id,
                        message: `SelfId "${id}" bị thiếu trong bản dịch`,
                    });
                }
            }

            // Find extra SelfIds
            for (const id of translatedIds) {
                if (!originalIds.has(id)) {
                    issues.push({
                        type: "extra",
                        selfId: id,
                        message: `SelfId "${id}" được thêm vào bản dịch (không có trong gốc)`,
                    });
                }
            }

            // Compare existing entries
            const originalMap = new Map(
                originalEntries.map((e) => [e.selfId, e])
            );
            const translatedMap = new Map(
                translatedEntries.map((e) => [e.selfId, e])
            );

            for (const [id, originalEntry] of originalMap) {
                const translatedEntry = translatedMap.get(id);
                if (translatedEntry) {
                    // Check if SelfId was modified
                    if (originalEntry.selfId !== translatedEntry.selfId) {
                        issues.push({
                            type: "modified_id",
                            selfId: id,
                            message: `SelfId bị thay đổi từ "${originalEntry.selfId}" thành "${translatedEntry.selfId}"`,
                        });
                    }

                    // Check for text changes
                    if (originalEntry.text !== translatedEntry.text) {
                        changes.push({
                            selfId: id,
                            original: originalEntry.text,
                            translated: translatedEntry.text,
                        });
                    }

                    // Check for tag modifications
                    const originalTags =
                        originalEntry.text.match(/<[^>]+>/g) || [];
                    const translatedTags =
                        translatedEntry.text.match(/<[^>]+>/g) || [];
                    const originalSpecialTags =
                        originalEntry.text.match(/\{[^}]+\}/g) || [];
                    const translatedSpecialTags =
                        translatedEntry.text.match(/\{[^}]+\}/g) || [];

                    if (originalTags.length !== translatedTags.length) {
                        issues.push({
                            type: "tag_count",
                            selfId: id,
                            message: `Số lượng tag HTML thay đổi: ${originalTags.length} → ${translatedTags.length}`,
                        });
                    }

                    if (
                        originalSpecialTags.length !==
                        translatedSpecialTags.length
                    ) {
                        issues.push({
                            type: "special_tag_count",
                            selfId: id,
                            message: `Số lượng special tag thay đổi: ${originalSpecialTags.length} → ${translatedSpecialTags.length}`,
                        });
                    }

                    const gameTagsOriginal =
                        originalEntry.text.match(/<(KEY_WAIT|NO_INPUT|cf)>/g) ||
                        [];
                    const gameTagsTranslated =
                        translatedEntry.text.match(
                            /<(KEY_WAIT|NO_INPUT|cf)>/g
                        ) || [];

                    if (gameTagsOriginal.length !== gameTagsTranslated.length) {
                        issues.push({
                            type: "game_tag",
                            selfId: id,
                            message: `Game tag bị thay đổi: ${gameTagsOriginal.join(
                                ", "
                            )}`,
                        });
                    }
                }
            }

            setComparisonResult({
                issues,
                changes,
                totalOriginal: originalEntries.length,
                totalTranslated: translatedEntries.length,
            });
        } catch (error) {
            setComparisonResult({
                error: `Lỗi: ${error.message}`,
                issues: [],
                changes: [],
            });
        }
    };

    return (
        <div>
            <h1>Game Translation Checker</h1>
            <p>
                Kiểm tra bản dịch game file - Đảm bảo không thay đổi SelfId và
                tag hệ thống
            </p>

            <div style={{ display: "flex", gap: "20px", marginBottom: "20px" }}>
                <div
                    style={{ flex: 1 }}
                    onDrop={(e) => handleDrop(e, setOriginalText)}
                    onDragOver={handleDragOver}
                >
                    <h3>File Gốc:</h3>
                    <textarea
                        value={originalText}
                        onChange={(e) => setOriginalText(e.target.value)}
                        placeholder="Paste file gốc vào đây hoặc kéo thả file..."
                        style={{
                            width: "100%",
                            height: "400px",
                            fontFamily: "monospace",
                            border: "2px dashed #ccc",
                            padding: "10px",
                        }}
                    />
                </div>

                <div
                    style={{ flex: 1 }}
                    onDrop={(e) => handleDrop(e, setTranslatedText)}
                    onDragOver={handleDragOver}
                >
                    <h3>Bản Dịch:</h3>
                    <textarea
                        value={translatedText}
                        onChange={(e) => setTranslatedText(e.target.value)}
                        placeholder="Paste bản dịch vào đây hoặc kéo thả file..."
                        style={{
                            width: "100%",
                            height: "400px",
                            fontFamily: "monospace",
                            border: "2px dashed #ccc",
                            padding: "10px",
                        }}
                    />
                </div>
            </div>

            <button
                onClick={compareFiles}
                disabled={!originalText || !translatedText}
                style={{
                    padding: "10px 20px",
                    fontSize: "16px",
                    marginBottom: "20px",
                }}
            >
                So Sánh
            </button>

            {comparisonResult && (
                <div>
                    <h2>Kết Quả:</h2>

                    {comparisonResult.error ? (
                        <div
                            style={{
                                color: "red",
                                backgroundColor: "#ffebee",
                                padding: "10px",
                                marginBottom: "10px",
                            }}
                        >
                            {comparisonResult.error}
                        </div>
                    ) : (
                        <>
                            <div style={{ marginBottom: "20px" }}>
                                <strong>Tổng entries:</strong>{" "}
                                {comparisonResult.totalOriginal} →{" "}
                                {comparisonResult.totalTranslated} |
                                <strong
                                    style={{ color: "red", marginLeft: "10px" }}
                                >
                                    Vấn đề:
                                </strong>{" "}
                                {comparisonResult.issues.length} |
                                <strong
                                    style={{
                                        color: "green",
                                        marginLeft: "10px",
                                    }}
                                >
                                    Đã dịch:
                                </strong>{" "}
                                {comparisonResult.changes.length}
                            </div>

                            {comparisonResult.issues.length > 0 && (
                                <div style={{ marginBottom: "20px" }}>
                                    <h3 style={{ color: "red" }}>
                                        ⚠️ Vấn Đề Phát Hiện (
                                        {comparisonResult.issues.length}):
                                    </h3>
                                    {comparisonResult.issues.map(
                                        (issue, index) => (
                                            <div
                                                key={index}
                                                style={{
                                                    backgroundColor: "#ffebee",
                                                    padding: "10px",
                                                    margin: "5px 0",
                                                    border: "1px solid red",
                                                }}
                                            >
                                                <strong>{issue.selfId}:</strong>{" "}
                                                {issue.message}
                                            </div>
                                        )
                                    )}
                                </div>
                            )}

                            {comparisonResult.changes.length > 0 && (
                                <div>
                                    <h3 style={{ color: "green" }}>
                                        ✅ Thay Đổi Text (Dịch thuật) (
                                        {comparisonResult.changes.length}):
                                    </h3>
                                    <div
                                        style={{
                                            maxHeight: "400px",
                                            overflowY: "auto",
                                        }}
                                    >
                                        {comparisonResult.changes.map(
                                            (change, index) => (
                                                <div
                                                    key={index}
                                                    style={{
                                                        backgroundColor:
                                                            "#e8f5e8",
                                                        padding: "10px",
                                                        margin: "5px 0",
                                                        border: "1px solid green",
                                                    }}
                                                >
                                                    <strong>
                                                        {change.selfId}
                                                    </strong>
                                                    <div
                                                        style={{
                                                            display: "flex",
                                                            gap: "20px",
                                                            marginTop: "10px",
                                                        }}
                                                    >
                                                        <div
                                                            style={{ flex: 1 }}
                                                        >
                                                            <div>
                                                                <strong>
                                                                    Gốc:
                                                                </strong>
                                                            </div>
                                                            <div
                                                                style={{
                                                                    backgroundColor:
                                                                        "#f5f5f5",
                                                                    padding:
                                                                        "5px",
                                                                    fontFamily:
                                                                        "monospace",
                                                                    fontSize:
                                                                        "12px",
                                                                }}
                                                            >
                                                                {
                                                                    change.original
                                                                }
                                                            </div>
                                                        </div>
                                                        <div
                                                            style={{ flex: 1 }}
                                                        >
                                                            <div>
                                                                <strong>
                                                                    Dịch:
                                                                </strong>
                                                            </div>
                                                            <div
                                                                style={{
                                                                    backgroundColor:
                                                                        "#e3f2fd",
                                                                    padding:
                                                                        "5px",
                                                                    fontFamily:
                                                                        "monospace",
                                                                    fontSize:
                                                                        "12px",
                                                                }}
                                                            >
                                                                {
                                                                    change.translated
                                                                }
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            )
                                        )}
                                    </div>
                                </div>
                            )}

                            {comparisonResult.issues.length === 0 && (
                                <div
                                    style={{
                                        backgroundColor: "#e8f5e8",
                                        padding: "15px",
                                        textAlign: "center",
                                        color: "green",
                                    }}
                                >
                                    <strong>
                                        ✅ Không phát hiện vấn đề nào!
                                    </strong>
                                    <br />
                                    Bản dịch an toàn, không thay đổi SelfId hay
                                    tag hệ thống.
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default GameTranslationChecker;
