import { useEffect, useState } from "react";
import { ApiClient } from "../lib/apiClient";

interface UserDashboardProps {
    userId: string;
    userName: string;
    sessionToken: string | null;
    apiUrl: string;
}

export default function UserDashboard({ userName, sessionToken, apiUrl }: UserDashboardProps) {
    const [apiKey, setApiKey] = useState<string | null>(null);
    const [apiKeyCreatedAt, setApiKeyCreatedAt] = useState<number | null>(null);
    const [apiKeyLastUsed, setApiKeyLastUsed] = useState<number | null>(null);
    const [apiKeyError, setApiKeyError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [showApiKeyModal, setShowApiKeyModal] = useState(false);
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [modalApiKey, setModalApiKey] = useState<string>("");
    const [copyButtonText, setCopyButtonText] = useState("📋 Copy Key");

    const apiClient = new ApiClient(apiUrl, async () => sessionToken || "");

    const fetchApiKey = async () => {
        if (!sessionToken) {
            setApiKeyError("No session token available");
            return;
        }

        try {
            const keyData = await apiClient.getApiKey();

            if (keyData.exists) {
                // Key exists but is masked
                setApiKey(keyData.key);
                setApiKeyCreatedAt(keyData.createdAt || null);
                setApiKeyLastUsed(keyData.lastUsed || null);
            } else if (keyData.key) {
                // New key was generated, show it in full
                setApiKey(keyData.key);
                setApiKeyCreatedAt(keyData.createdAt || null);
                setModalApiKey(keyData.key);
                setShowApiKeyModal(true);
            }
        } catch (error) {
            console.error("Failed to fetch API key:", error);
            setApiKeyError(error instanceof Error ? error.message : "Failed to fetch API key");
        }
    };

    useEffect(() => {
        // Fetch initial API key
        fetchApiKey();
    });

    const regenerateApiKey = async () => {
        setShowConfirmModal(false);
        setLoading(true);
        try {
            const response = await apiClient.regenerateApiKey();
            if (response.key) {
                setModalApiKey(response.key);
                setApiKey(response.key);
                setApiKeyCreatedAt(response.createdAt || null);
                setApiKeyLastUsed(null);
                setShowApiKeyModal(true);
            }
        } catch (error) {
            console.error("Failed to regenerate key:", error);
            setApiKeyError(error instanceof Error ? error.message : "Failed to regenerate API key");
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopyButtonText("Copied!");
            setTimeout(() => {
                setCopyButtonText("📋 Copy Key");
            }, 2000);
        } catch (err) {
            console.error("Failed to copy:", err);
        }
    };

    const closeApiKeyModal = () => {
        setShowApiKeyModal(false);
        // Reload to show masked version
        window.location.reload();
    };

    const usageExample = `# Authenticate with your API key
curl -H "Authorization: Bearer YOUR_API_KEY" \\
  https://ids.moe/mal/1

# Or use it as a query parameter
curl https://ids.moe/mal/1?key=YOUR_API_KEY`;

    return (
        <div className="max-w-4xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg overflow-hidden">
                <div className="px-6 py-8 border-b border-gray-200 dark:border-gray-700">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Dashboard</h1>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">Welcome back, {userName}!</p>
                </div>

                <div className="px-6 py-8">
                    {apiKeyError && (
                        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                            <p className="text-sm text-red-600 dark:text-red-400">
                                Error loading API key: {apiKeyError}
                            </p>
                        </div>
                    )}

                    <div className="mb-8">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Your API Key</h2>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            Use this key to authenticate your requests to the ids.moe API. Keep it secure and don't
                            share it publicly.
                        </p>

                        {apiKeyCreatedAt && (
                            <div className="text-xs text-gray-500 dark:text-gray-500 mb-2">
                                Created: {new Date(apiKeyCreatedAt).toLocaleString()}
                                {apiKeyLastUsed && (
                                    <span> • Last used: {new Date(apiKeyLastUsed).toLocaleString()}</span>
                                )}
                            </div>
                        )}

                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            {apiKey && (
                                apiKey.includes("...") ? (
                                    // Masked key display
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1 mr-4">
                                            <code className="text-sm font-mono text-gray-600 dark:text-gray-400">
                                                {apiKey}
                                            </code>
                                            <p className="text-xs text-gray-500 mt-1">
                                                Key is masked for security. Full key was shown only once when generated.
                                            </p>
                                        </div>
                                        <div className="flex space-x-2">
                                            <button
                                                type="button"
                                                onClick={() => setShowConfirmModal(true)}
                                                disabled={loading}
                                                className="px-3 py-1 text-sm bg-orange-600 text-white rounded hover:bg-orange-700 transition-colors disabled:opacity-50"
                                            >
                                                {loading ? "Processing..." : "Regenerate"}
                                            </button>
                                        </div>
                                    </div>
                                ) : null
                            )}
                        </div>
                    </div>

                    <div className="mb-8">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Usage Example</h2>
                        <div className="bg-gray-900 rounded-lg p-4 text-white">
                            <pre className="text-sm overflow-x-auto">{usageExample}</pre>
                        </div>
                    </div>

                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
                            API Documentation
                        </h2>
                        <div>
                            <a
                                href="/docs"
                                className="block p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                            >
                                <h3 className="font-semibold text-gray-900 dark:text-gray-100">API Reference</h3>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                    Learn about available endpoints and response formats
                                </p>
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            {/* API Key Modal */}
            {showApiKeyModal && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6 relative">
                        <div className="text-center mb-6">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                                🔑 Your New API Key
                            </h3>
                            <p className="text-sm text-orange-600 dark:text-orange-400 mb-4">
                                ⚠️ This is the only time you'll see the full key. Copy it now!
                            </p>
                        </div>

                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-6">
                            <code className="text-sm font-mono text-gray-900 dark:text-gray-100 break-all">
                                {modalApiKey}
                            </code>
                        </div>

                        <div className="flex space-x-3">
                            <button
                                type="button"
                                onClick={() => copyToClipboard(modalApiKey)}
                                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors"
                            >
                                {copyButtonText}
                            </button>
                            <button
                                type="button"
                                onClick={closeApiKeyModal}
                                className="px-4 py-2 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors"
                            >
                                I've Copied It
                            </button>
                        </div>

                        <p className="text-xs text-gray-500 mt-4 text-center">
                            After closing this dialog, only a masked version will be shown for security.
                        </p>
                    </div>
                </div>
            )}

            {/* Confirmation Modal */}
            {showConfirmModal && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6 relative">
                        <div className="text-center mb-6">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                                🔄 Regenerate API Key?
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                This will invalidate your current API key and any applications using it will stop
                                working.
                            </p>
                        </div>

                        <div className="flex space-x-3">
                            <button
                                type="button"
                                onClick={() => setShowConfirmModal(false)}
                                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={regenerateApiKey}
                                className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                            >
                                Yes, Regenerate
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
