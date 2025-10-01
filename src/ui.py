def get_ui_html() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal Knowledge Graph</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover {
            background: #f8f9ff;
            border-color: #764ba2;
        }
        .upload-area.dragover {
            background: #f0f4ff;
            border-color: #4c51bf;
        }
        input[type="file"] {
            display: none;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .query-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            margin-bottom: 15px;
        }
        .query-input:focus {
            outline: none;
            border-color: #667eea;
        }
        .results {
            margin-top: 20px;
        }
        .result-item {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        .result-item .source {
            color: #667eea;
            font-weight: bold;
            font-size: 0.9em;
        }
        .result-item .snippet {
            color: #555;
            margin: 10px 0;
            line-height: 1.6;
        }
        .result-item .score {
            color: #999;
            font-size: 0.85em;
        }
        .answer-box {
            background: #e6f3ff;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #2196F3;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
        }
        .stat-item {
            text-align: center;
            padding: 20px;
        }
        .stat-item .number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-item .label {
            color: #666;
            margin-top: 5px;
        }
        .status {
            padding: 10px 15px;
            border-radius: 6px;
            margin-top: 15px;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .text-area {
            width: 100%;
            min-height: 200px;
            padding: 15px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            font-family: inherit;
            resize: vertical;
            margin-bottom: 15px;
        }
        .text-area:focus {
            outline: none;
            border-color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Personal Knowledge Graph</h1>
            <p>Build and query your personal knowledge graph from notes and documents</p>
        </div>

        <div class="card">
            <h2>📊 Graph Statistics</h2>
            <div class="stats" id="stats">
                <div class="stat-item">
                    <div class="number">0</div>
                    <div class="label">Triples</div>
                </div>
                <div class="stat-item">
                    <div class="number">0</div>
                    <div class="label">Entities</div>
                </div>
                <div class="stat-item">
                    <div class="number">-</div>
                    <div class="label">Embedding Method</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📤 Upload Documents</h2>
            <div class="upload-area" id="uploadArea">
                <p style="font-size: 1.2em; margin-bottom: 10px;">📄 Drop files here or click to browse</p>
                <p style="color: #666;">Supports: .txt, .md files</p>
                <input type="file" id="fileInput" multiple accept=".txt,.md">
            </div>
            <div style="text-align: center; margin-top: 20px;">
                <button class="btn" id="uploadBtn">Upload & Process</button>
            </div>
            <div class="status" id="uploadStatus"></div>
            <div class="loading" id="uploadLoading">
                <div class="spinner"></div>
                <p style="margin-top: 10px;">Processing files...</p>
            </div>
        </div>

        <div class="card">
            <h2>📝 Paste Document Text</h2>
            <textarea class="text-area" id="textInput" placeholder="Paste your document text here..."></textarea>
            <input type="text" class="query-input" id="titleInput" placeholder="Document title (optional)" style="margin-bottom: 15px;">
            <button class="btn" id="textBtn">Process Text</button>
            <div class="status" id="textStatus"></div>
            <div class="loading" id="textLoading">
                <div class="spinner"></div>
                <p style="margin-top: 10px;">Processing text...</p>
            </div>
        </div>

        <div class="card">
            <h2>🔍 Query Knowledge Graph</h2>
            <input type="text" class="query-input" id="queryInput" placeholder="Ask a question about your knowledge graph...">
            <button class="btn" id="queryBtn">Search</button>
            <div class="loading" id="queryLoading">
                <div class="spinner"></div>
                <p style="margin-top: 10px;">Searching...</p>
            </div>
            <div class="results" id="results"></div>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const uploadStatus = document.getElementById('uploadStatus');
        const uploadLoading = document.getElementById('uploadLoading');
        const textInput = document.getElementById('textInput');
        const titleInput = document.getElementById('titleInput');
        const textBtn = document.getElementById('textBtn');
        const textStatus = document.getElementById('textStatus');
        const textLoading = document.getElementById('textLoading');
        const queryInput = document.getElementById('queryInput');
        const queryBtn = document.getElementById('queryBtn');
        const queryLoading = document.getElementById('queryLoading');
        const results = document.getElementById('results');

        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            fileInput.files = e.dataTransfer.files;
        });

        uploadBtn.addEventListener('click', async () => {
            const files = fileInput.files;
            if (files.length === 0) {
                alert('Please select files to upload');
                return;
            }

            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }

            uploadLoading.classList.add('active');
            uploadStatus.className = 'status';
            uploadBtn.disabled = true;

            try {
                const response = await fetch('/api/ingest', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                uploadStatus.className = 'status success';
                uploadStatus.textContent = `✓ Successfully processed ${files.length} file(s). Added ${data.triples} triples to the graph.`;
                
                fileInput.value = '';
                loadStats();
            } catch (error) {
                uploadStatus.className = 'status error';
                uploadStatus.textContent = `✗ Error: ${error.message}`;
            } finally {
                uploadLoading.classList.remove('active');
                uploadBtn.disabled = false;
            }
        });

        textBtn.addEventListener('click', async () => {
            const text = textInput.value.trim();
            if (!text) {
                alert('Please paste some text to process');
                return;
            }

            const title = titleInput.value.trim() || 'pasted_text';

            textLoading.classList.add('active');
            textStatus.className = 'status';
            textBtn.disabled = true;

            try {
                const response = await fetch('/api/ingest-text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, title: title })
                });
                const data = await response.json();
                
                textStatus.className = 'status success';
                textStatus.textContent = `✓ Successfully processed text. Added ${data.triples} triples to the graph.`;
                
                textInput.value = '';
                titleInput.value = '';
                loadStats();
            } catch (error) {
                textStatus.className = 'status error';
                textStatus.textContent = `✗ Error: ${error.message}`;
            } finally {
                textLoading.classList.remove('active');
                textBtn.disabled = false;
            }
        });

        queryBtn.addEventListener('click', async () => {
            const query = queryInput.value.trim();
            if (!query) {
                alert('Please enter a query');
                return;
            }

            queryLoading.classList.add('active');
            results.innerHTML = '';
            queryBtn.disabled = true;

            try {
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ q: query, top_k: 5 })
                });
                const data = await response.json();
                
                if (data.answer) {
                    results.innerHTML = `<div class="answer-box"><strong>Answer:</strong> ${data.answer}</div>`;
                }
                
                if (data.results && data.results.length > 0) {
                    data.results.forEach(result => {
                        const item = document.createElement('div');
                        item.className = 'result-item';
                        item.innerHTML = `
                            <div class="source">📄 ${result.source}</div>
                            <div class="snippet">${result.snippet}</div>
                            <div class="score">Relevance: ${(result.score * 100).toFixed(1)}%</div>
                        `;
                        results.appendChild(item);
                    });
                } else {
                    results.innerHTML += '<p style="color: #999; text-align: center; padding: 20px;">No results found.</p>';
                }
            } catch (error) {
                results.innerHTML = `<div class="status error">✗ Error: ${error.message}</div>`;
            } finally {
                queryLoading.classList.remove('active');
                queryBtn.disabled = false;
            }
        });

        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                queryBtn.click();
            }
        });

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.querySelector('#stats').innerHTML = `
                    <div class="stat-item">
                        <div class="number">${data.total_triples}</div>
                        <div class="label">Triples</div>
                    </div>
                    <div class="stat-item">
                        <div class="number">${data.total_entities}</div>
                        <div class="label">Entities</div>
                    </div>
                    <div class="stat-item">
                        <div class="number">${data.embedding_method}</div>
                        <div class="label">Embedding Method</div>
                    </div>
                `;
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }

        loadStats();
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
    """
