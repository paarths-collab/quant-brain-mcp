"use client";

import { useState, useEffect } from "react";
import { Download, FileText, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function ReportPage() {
    const [reportHtml, setReportHtml] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // Fetch the report HTML when component mounts
        async function fetchReport() {
            try {
                const res = await fetch("http://localhost:8000/api/reports/view/portfolio");
                if (!res.ok) {
                    if (res.status === 404) throw new Error("Report not generated yet.");
                    throw new Error("Failed to load report.");
                }
                const html = await res.text();
                setReportHtml(html);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        fetchReport();
    }, []);

    const handleDownloadPdf = async () => {
        window.open("http://localhost:8000/api/reports/download/portfolio/pdf", "_blank");
    };

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Analysis Report</h1>
                    <p className="text-gray-400 text-sm">Comprehensive portfolio performance review</p>
                </div>
                <button
                    onClick={handleDownloadPdf}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white font-medium transition-colors"
                >
                    <Download size={18} />
                    Download PDF
                </button>
            </div>

            <div className="flex-1 glass-panel overflow-hidden relative">
                {loading && (
                    <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mr-3"></div>
                        Loading report...
                    </div>
                )}

                {error && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-red-400">
                        <AlertCircle size={48} className="mb-4 opacity-50" />
                        <p className="text-lg">{error}</p>
                        <p className="text-sm text-gray-500 mt-2">Run a new analysis to generate this report.</p>
                    </div>
                )}

                {reportHtml && (
                    <iframe
                        srcDoc={reportHtml}
                        title="Portfolio Report"
                        className="w-full h-full border-none bg-white rounded-lg"
                        sandbox="allow-scripts allow-same-origin"
                    />
                )}
            </div>
        </div>
    );
}
