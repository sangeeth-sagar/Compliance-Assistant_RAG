<script setup>
import { ref, onMounted, computed, watch } from 'vue';

const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : '';

// Navigation & Global state
const currentTab = ref('scan');
const documents = ref([]);
const selectedDocId = ref(null);
const selectedDoc = ref(null);
const auditLogs = ref([]);

// UI Loading indicators
const isScanning = ref(false);
const isSummarizing = ref(false);
const isIndexing = ref(false);
const isQuerying = ref(false);
const globalLoading = ref(false);
const errorMessage = ref('');

// Scan options & input
const selectedFile = ref(null);
const useSpacy = ref(false);
const scanResult = ref(null);
const dragOver = ref(false);

// Chat & Q&A state
const chatQuestion = ref('');
const chatHistories = ref({}); // Map of doc_id -> list of messages

// Audit Search
const auditSearch = ref('');

// Fetch list of documents
const fetchDocuments = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/documents`);
    if (!res.ok) throw new Error('Failed to load documents');
    documents.value = await res.json();
    
    // Automatically select the first document if none selected
    if (documents.value.length > 0 && !selectedDocId.value) {
      selectedDocId.value = documents.value[documents.value.length - 1].id;
    }
  } catch (err) {
    console.error(err);
    errorMessage.value = err.message;
  }
};

// Fetch full document details (raw text, redacted text, summary)
const fetchDocumentDetails = async (docId) => {
  if (!docId) return;
  globalLoading.value = true;
  try {
    const res = await fetch(`${API_BASE}/api/documents/${docId}`);
    if (!res.ok) throw new Error('Failed to fetch document details');
    selectedDoc.value = await res.json();
  } catch (err) {
    console.error(err);
    errorMessage.value = err.message;
  } finally {
    globalLoading.value = false;
  }
};

// Fetch audit logs
const fetchAuditLogs = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/audit`);
    if (!res.ok) throw new Error('Failed to fetch audit logs');
    auditLogs.value = await res.json();
  } catch (err) {
    console.error(err);
  }
};

// Watchers
watch(selectedDocId, (newId) => {
  if (newId) {
    fetchDocumentDetails(newId);
  } else {
    selectedDoc.value = null;
  }
});

onMounted(() => {
  fetchDocuments();
  fetchAuditLogs();
});

// File input handlers
const handleFileChange = (e) => {
  const file = e.target.files[0];
  if (file) {
    selectedFile.value = file;
    scanResult.value = null;
  }
};

const handleDrop = (e) => {
  dragOver.value = false;
  const file = e.dataTransfer.files[0];
  if (file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (['pdf', 'txt', 'csv'].includes(ext)) {
      selectedFile.value = file;
      scanResult.value = null;
    } else {
      alert('Unsupported file type. Only PDF, TXT, and CSV files are allowed.');
    }
  }
};

// Submit document for scanning
const scanDocument = async () => {
  if (!selectedFile.value) return;
  isScanning.value = true;
  errorMessage.value = '';
  
  const formData = new FormData();
  formData.append('file', selectedFile.value);
  formData.append('use_spacy', useSpacy.value);
  
  try {
    const res = await fetch(`${API_BASE}/api/scan`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'Scan failed');
    }
    
    const result = await res.json();
    scanResult.value = result;
    selectedDocId.value = result.id;
    
    // Refresh documents & audit logs list
    await fetchDocuments();
    await fetchAuditLogs();
    
    // Auto navigate to the document details tab
    currentTab.value = 'documents';
  } catch (err) {
    console.error(err);
    errorMessage.value = err.message;
  } finally {
    isScanning.value = false;
  }
};

// Generate summary via LLM
const generateSummary = async () => {
  if (!selectedDocId.value) return;
  isSummarizing.value = true;
  errorMessage.value = '';
  try {
    const res = await fetch(`${API_BASE}/api/documents/${selectedDocId.value}/summary`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to generate compliance summary');
    const data = await res.json();
    if (selectedDoc.value) {
      selectedDoc.value.summary = data.summary;
      selectedDoc.value.has_summary = true;
    }
    // Update local lists
    await fetchDocuments();
    await fetchAuditLogs();
  } catch (err) {
    errorMessage.value = err.message;
  } finally {
    isSummarizing.value = false;
  }
};

// Index Document for RAG
const indexDocument = async () => {
  if (!selectedDocId.value) return;
  isIndexing.value = true;
  errorMessage.value = '';
  try {
    const res = await fetch(`${API_BASE}/api/documents/${selectedDocId.value}/index`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to index document');
    const data = await res.json();
    if (selectedDoc.value) {
      selectedDoc.value.indexed = true;
    }
    alert(`Successfully indexed document into vector database! Created ${data.chunks} chunks.`);
    await fetchDocuments();
  } catch (err) {
    errorMessage.value = err.message;
  } finally {
    isIndexing.value = false;
  }
};

// Query RAG (Chatbot)
const submitQuery = async () => {
  const query = chatQuestion.value.trim();
  if (!query || !selectedDocId.value) return;
  
  if (!chatHistories.value[selectedDocId.value]) {
    chatHistories.value[selectedDocId.value] = [];
  }
  
  // Append user message
  chatHistories.value[selectedDocId.value].push({
    role: 'user',
    content: query,
  });
  
  chatQuestion.value = '';
  isQuerying.value = true;
  
  try {
    const res = await fetch(`${API_BASE}/api/documents/${selectedDocId.value}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: query }),
    });
    
    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'QA failed');
    }
    
    const data = await res.json();
    
    // Append AI reply
    chatHistories.value[selectedDocId.value].push({
      role: 'assistant',
      content: data.answer,
    });
    
    await fetchAuditLogs();
  } catch (err) {
    chatHistories.value[selectedDocId.value].push({
      role: 'assistant',
      content: `Error: ${err.message}`,
    });
  } finally {
    isQuerying.value = false;
  }
};

// Filtered audit logs
const filteredAuditLogs = computed(() => {
  const query = auditSearch.value.toLowerCase().trim();
  if (!query) return auditLogs.value;
  return auditLogs.value.filter(log => 
    log.filename.toLowerCase().includes(query) ||
    log.action.toLowerCase().includes(query) ||
    (log.risk_level && log.risk_level.toLowerCase().includes(query)) ||
    log.doc_id.toLowerCase().includes(query)
  );
});

// Format Date
const formatDate = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  return date.toLocaleString();
};

// Format File Size
const formatSize = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Simple custom Markdown rendering function
const formatMarkdown = (text) => {
  if (!text) return '';
  
  // Basic markdown rendering to keep it dependency-free and fast
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
    
  // Headers
  html = html.replace(/^### (.*$)/gim, '<h4 class="summary-h3">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 class="summary-h2">$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2 class="summary-h1">$1</h2>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Lists
  html = html.replace(/^\s*-\s+(.*$)/gim, '<li class="summary-li">$1</li>');
  
  // Line breaks
  html = html.replace(/\n/g, '<br>');
  
  return html;
};
</script>

<template>
  <div class="app-container">
    <!-- Sidebar Navigation -->
    <aside class="sidebar">
      <div class="logo-container">
        <span class="nav-icon" style="font-size: 1.6rem; color: #58a6ff;">🛡️</span>
        <div class="logo-text">Compliance Sentinel</div>
      </div>
      
      <nav class="nav-links">
        <div 
          class="nav-item" 
          :class="{ active: currentTab === 'scan' }" 
          @click="currentTab = 'scan'"
        >
          <span class="nav-icon">📤</span>
          <span>Scan Document</span>
        </div>
        <div 
          class="nav-item" 
          :class="{ active: currentTab === 'documents' }" 
          @click="currentTab = 'documents'; fetchDocuments();"
        >
          <span class="nav-icon">📂</span>
          <span>Document Explorer</span>
        </div>
        <div 
          class="nav-item" 
          :class="{ active: currentTab === 'chat' }" 
          @click="currentTab = 'chat'; fetchDocuments();"
        >
          <span class="nav-icon">💬</span>
          <span>AI Chat / RAG</span>
        </div>
        <div 
          class="nav-item" 
          :class="{ active: currentTab === 'audit' }" 
          @click="currentTab = 'audit'; fetchAuditLogs();"
        >
          <span class="nav-icon">📜</span>
          <span>Audit Log</span>
        </div>
      </nav>
      
      <div class="sidebar-footer">
        <div>Internship Assignment</div>
        <div style="font-size: 0.75rem; margin-top: 4px;">Proteccio Data © 2026</div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="main-content">
      <!-- Error Message Banner -->
      <div v-if="errorMessage" class="alert alert-info animated" style="margin-bottom: 24px; background: rgba(248, 81, 73, 0.1); border-color: rgba(248, 81, 73, 0.2); color: #ff7b72;">
        <span style="font-size: 1.2rem;">⚠️</span>
        <div style="flex-grow: 1;">
          <strong>Error:</strong> {{ errorMessage }}
        </div>
        <button class="btn-text" @click="errorMessage = ''" style="background: none; border: none; color: inherit; cursor: pointer; font-size: 1.1rem;">×</button>
      </div>

      <!-- SCAN TAB -->
      <section v-if="currentTab === 'scan'" class="tab-content animated">
        <div class="page-header">
          <h1 class="page-title">Scan New Document</h1>
          <p class="page-description">Upload PDFs, CSVs, or text files to audit risk scoring, redact PII and evaluate compliance.</p>
        </div>

        <div class="grid-2">
          <!-- Upload Controls -->
          <div class="card glass-panel flex-column" style="gap: 20px;">
            <h2 style="font-size: 1.25rem; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
              <span>📁</span> Select File
            </h2>
            
            <div 
              class="drag-drop-zone"
              :class="{ active: dragOver }"
              @dragover.prevent="dragOver = true"
              @dragleave.prevent="dragOver = false"
              @drop.prevent="handleDrop"
              @click="$refs.fileInput.click()"
            >
              <input 
                type="file" 
                ref="fileInput" 
                @change="handleFileChange" 
                accept=".pdf,.txt,.csv" 
                style="display: none;"
              />
              
              <div v-if="!selectedFile" class="drag-drop-placeholder">
                <span class="upload-cloud-icon">☁️</span>
                <p style="font-weight: 600; margin: 12px 0 6px 0; color: var(--text-bright);">Drag & Drop your document here</p>
                <p style="font-size: 0.85rem; color: var(--text-muted);">Supports PDF, TXT, CSV (Max 15MB)</p>
              </div>
              <div v-else class="selected-file-display">
                <span class="file-icon-big">📄</span>
                <p style="font-weight: 600; margin: 8px 0 4px 0; color: var(--text-bright);">{{ selectedFile.name }}</p>
                <p style="font-size: 0.85rem; color: var(--text-muted);">{{ formatSize(selectedFile.size) }}</p>
              </div>
            </div>

            <!-- Configuration Options -->
            <div class="scan-options" style="background: rgba(255,255,255,0.02); padding: 16px; border-radius: 8px; border: 1px solid var(--border-color);">
              <label class="checkbox-container" style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                <input type="checkbox" v-model="useSpacy" style="transform: scale(1.15);" />
                <div>
                  <span style="font-weight: 600; color: var(--text-normal); display: block; font-size: 0.9rem;">Enable spaCy NER (Names / Orgs)</span>
                  <span style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-top: 2px;">Uses NLP models to extract person and organization entities alongside regex logic.</span>
                </div>
              </label>
            </div>

            <!-- Buttons -->
            <div style="display: flex; gap: 12px; margin-top: 10px;">
              <button 
                class="btn btn-primary" 
                style="flex-grow: 1; height: 48px;" 
                :disabled="!selectedFile || isScanning"
                @click="scanDocument"
              >
                <span v-if="isScanning" class="spinner">⏳</span>
                <span v-else>🛡️</span>
                <span>{{ isScanning ? 'Processing & Redacting...' : 'Analyze Document' }}</span>
              </button>
              
              <button 
                v-if="selectedFile" 
                class="btn btn-secondary" 
                @click="selectedFile = null; scanResult = null;"
                :disabled="isScanning"
              >
                Clear
              </button>
            </div>
          </div>

          <!-- Quick Info Panel -->
          <div class="card glass-panel flex-column" style="gap: 16px; background: rgba(56, 139, 253, 0.03);">
            <h2 style="font-size: 1.25rem;">Security & Privacy Safeguards</h2>
            <ul class="info-list" style="margin: 0; padding-left: 20px; color: var(--text-muted); display: flex; flex-direction: column; gap: 12px;">
              <li><strong>Zero PII Leakage:</strong> All sensitive identifiers are fully redacted locally before document contents are indexed in ChromaDB or forwarded to Gemini API.</li>
              <li><strong>Weighted Risk Assessment:</strong> Scoring assigns higher points to identity files (PAN, Aadhaar) and keys, mapping to High, Medium, or Low severity.</li>
              <li><strong>OCR Automatic Fallback:</strong> If text extraction fails on scanned PDFs, our OCR engine extracts optical characters using Tesseract automatically.</li>
              <li><strong>Append-only Audit Trails:</strong> All scans, summaries, and Q&A instances generate immutable tracking lines.</li>
            </ul>
            
            <div style="margin-top: auto; display: flex; justify-content: center;">
              <span style="font-size: 4rem; opacity: 0.25;">🛡️</span>
            </div>
          </div>
        </div>
      </section>

      <!-- DOCUMENT EXPLORER TAB -->
      <section v-if="currentTab === 'documents'" class="tab-content animated">
        <div class="page-header">
          <h1 class="page-title">Document Explorer</h1>
          <p class="page-description">Browse scanned documents, examine PII findings, and review compliance summaries.</p>
        </div>

        <div v-if="documents.length === 0" class="card glass-panel text-center" style="padding: 60px 24px;">
          <span style="font-size: 3rem; display: block; margin-bottom: 16px;">📂</span>
          <h2 style="font-size: 1.5rem; margin-bottom: 8px;">No Scanned Documents</h2>
          <p style="color: var(--text-muted); max-width: 480px; margin: 0 auto 20px auto;">
            You have not scanned any documents during this session yet. Upload a file to generate reports.
          </p>
          <button class="btn btn-primary" @click="currentTab = 'scan'">Scan Document</button>
        </div>

        <div v-else class="explorer-layout">
          <!-- Document Selector and Sidebar -->
          <div class="explorer-sidebar glass-panel">
            <h2 style="font-size: 1.1rem; padding: 16px; border-bottom: 1px solid var(--border-color); margin: 0;">
              Scanned Files ({{ documents.length }})
            </h2>
            <div class="doc-list-scroll">
              <div 
                v-for="doc in documents" 
                :key="doc.id" 
                class="doc-list-item" 
                :class="{ active: selectedDocId === doc.id }"
                @click="selectedDocId = doc.id"
              >
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; width: 100%;">
                  <span class="doc-filename" :title="doc.filename">{{ doc.filename }}</span>
                  <span 
                    class="badge" 
                    :class="{
                      'badge-high': doc.risk.level === 'High',
                      'badge-medium': doc.risk.level === 'Medium',
                      'badge-low': doc.risk.level === 'Low'
                    }"
                  >
                    {{ doc.risk.level }}
                  </span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 0.75rem; color: var(--text-muted);">
                  <span>Score: {{ doc.risk.score }}</span>
                  <span>ID: {{ doc.id }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Document Main Report Area -->
          <div class="explorer-report-area">
            <div v-if="globalLoading" class="card glass-panel text-center" style="padding: 100px 24px;">
              <span class="spinner" style="font-size: 2.5rem; display: block; margin-bottom: 16px;">⏳</span>
              <p>Loading document details...</p>
            </div>
            
            <div v-else-if="selectedDoc" class="report-content-flow animated">
              <!-- Summary Dashboard Row -->
              <div class="report-dashboard-grid">
                <div class="card glass-panel" :style="{ borderLeft: '4px solid ' + (selectedDoc.risk.level === 'High' ? 'var(--risk-high)' : selectedDoc.risk.level === 'Medium' ? 'var(--risk-medium)' : 'var(--risk-low)') }">
                  <div style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Risk Classification</div>
                  <div style="display: flex; align-items: baseline; gap: 10px; margin-top: 12px;">
                    <span 
                      style="font-size: 2rem; font-weight: 800;"
                      :style="{ color: selectedDoc.risk.level === 'High' ? 'var(--risk-high)' : selectedDoc.risk.level === 'Medium' ? 'var(--risk-medium)' : 'var(--risk-low)' }"
                    >
                      {{ selectedDoc.risk.level }}
                    </span>
                    <span style="color: var(--text-muted); font-size: 1.1rem;">(Score: {{ selectedDoc.risk.score }})</span>
                  </div>
                </div>

                <div class="card glass-panel">
                  <div style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Sensitive Instances</div>
                  <div style="font-size: 2rem; font-weight: 800; color: var(--text-bright); margin-top: 12px;">
                    {{ selectedDoc.risk.total_findings }}
                  </div>
                </div>

                <div class="card glass-panel">
                  <div style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">RAG Status</div>
                  <div style="margin-top: 12px; display: flex; align-items: center; gap: 8px;">
                    <span v-if="selectedDoc.indexed" style="color: var(--risk-low); font-weight: 600; font-size: 1.1rem; display: flex; align-items: center; gap: 6px;">
                      <span>✓</span> Indexed & Active
                    </span>
                    <span v-else style="color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
                      <span>○</span> Not Indexed
                    </span>
                  </div>
                </div>
              </div>

              <!-- PII Breakdown -->
              <div class="grid-2">
                <div class="card glass-panel">
                  <h3 style="font-size: 1.1rem; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
                    <span>🛡️</span> PII Finding Types
                  </h3>
                  
                  <div v-if="selectedDoc.risk.breakdown.length === 0" style="padding: 20px; text-align: center; color: var(--text-muted);">
                    No PII findings detected in this file.
                  </div>
                  <table v-else class="findings-table">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th style="text-align: center;">Count</th>
                        <th style="text-align: center;">Weight</th>
                        <th style="text-align: right;">Points</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="item in selectedDoc.risk.breakdown" :key="item.type">
                        <td><strong>{{ item.type }}</strong></td>
                        <td style="text-align: center;">{{ item.count }}</td>
                        <td style="text-align: center;">×{{ item.weight }}</td>
                        <td style="text-align: right; color: var(--text-bright);">+{{ item.points }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div class="card glass-panel flex-column" style="gap: 16px;">
                  <h3 style="font-size: 1.1rem; margin-bottom: 8px;">Compliance Actions</h3>
                  
                  <button 
                    class="btn btn-primary" 
                    @click="generateSummary" 
                    :disabled="isSummarizing"
                    style="width: 100%; height: 44px;"
                  >
                    <span v-if="isSummarizing" class="spinner">⏳</span>
                    <span v-else>🤖</span>
                    <span>{{ selectedDoc.summary ? 'Regenerate Summary' : 'Generate Compliance Summary' }}</span>
                  </button>

                  <button 
                    v-if="!selectedDoc.indexed"
                    class="btn btn-secondary" 
                    @click="indexDocument" 
                    :disabled="isIndexing"
                    style="width: 100%; height: 44px;"
                  >
                    <span v-if="isIndexing" class="spinner">⏳</span>
                    <span v-else>📥</span>
                    <span>Index for Q&A (RAG)</span>
                  </button>
                  <button 
                    v-else
                    class="btn btn-secondary" 
                    @click="currentTab = 'chat'"
                    style="width: 100%; height: 44px; background: rgba(56, 139, 253, 0.1); border-color: rgba(56, 139, 253, 0.3);"
                  >
                    <span>💬</span>
                    <span>Open in AI Chat</span>
                  </button>
                </div>
              </div>

              <!-- Compliance Summary Output -->
              <div v-if="selectedDoc.summary" class="card glass-panel animated" style="border-left: 4px solid var(--accent-primary);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                  <h3 style="font-size: 1.2rem; margin: 0; display: flex; align-items: center; gap: 8px;">
                    <span>📜</span> AI Compliance & Security Report
                  </h3>
                  <button class="btn btn-secondary btn-sm" @click="navigator.clipboard.writeText(selectedDoc.summary); alert('Copied summary to clipboard!');" style="padding: 6px 12px; font-size: 0.8rem;">
                    Copy Report
                  </button>
                </div>
                <div class="markdown-body" v-html="formatMarkdown(selectedDoc.summary)"></div>
              </div>

              <!-- Previews -->
              <div class="card glass-panel">
                <h3 style="font-size: 1.1rem; margin-bottom: 16px;">Document Content Inspection</h3>
                
                <div style="display: flex; flex-direction: column; gap: 20px;">
                  <div>
                    <h4 style="font-size: 0.95rem; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase;">Redacted Content Preview (Secure View)</h4>
                    <pre class="code-preview">{{ selectedDoc.redacted_text.slice(0, 3000) }}{{ selectedDoc.redacted_text.length > 3000 ? '\n... [TRUNCATED] ...' : '' }}</pre>
                  </div>

                  <div>
                    <h4 style="font-size: 0.95rem; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase;">Raw Content Preview (Unredacted - Local View)</h4>
                    <pre class="code-preview raw-preview">{{ selectedDoc.raw_text.slice(0, 1000) }}{{ selectedDoc.raw_text.length > 1000 ? '\n... [TRUNCATED] ...' : '' }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- AI CHAT / RAG TAB -->
      <section v-if="currentTab === 'chat'" class="tab-content animated">
        <div class="page-header">
          <h1 class="page-title">AI Chat Assistant (RAG)</h1>
          <p class="page-description">Ask questions about document content securely. All LLM contexts use redacted text models.</p>
        </div>

        <div v-if="documents.length === 0" class="card glass-panel text-center" style="padding: 60px 24px;">
          <span style="font-size: 3rem; display: block; margin-bottom: 16px;">💬</span>
          <h2 style="font-size: 1.5rem; margin-bottom: 8px;">No Scanned Documents</h2>
          <p style="color: var(--text-muted); max-width: 480px; margin: 0 auto 20px auto;">
            Please scan a document before starting a chat.
          </p>
          <button class="btn btn-primary" @click="currentTab = 'scan'">Scan Document</button>
        </div>

        <div v-else class="chat-workspace">
          <!-- Document selection bar -->
          <div class="card glass-panel" style="padding: 16px; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 12px; flex-grow: 1;">
              <span style="font-weight: 600; font-size: 0.95rem; flex-shrink: 0;">Active Document:</span>
              <select v-model="selectedDocId" class="doc-select-dropdown" style="flex-grow: 1; max-width: 400px;">
                <option v-for="doc in documents" :key="doc.id" :value="doc.id">
                  {{ doc.filename }} (ID: {{ doc.id }})
                </option>
              </select>
            </div>
            
            <div v-if="selectedDoc">
              <span v-if="selectedDoc.indexed" class="badge badge-low" style="height: 24px;">RAG Ready</span>
              <button 
                v-else 
                class="btn btn-primary" 
                style="height: 32px; padding: 0 16px; font-size: 0.8rem;" 
                @click="indexDocument" 
                :disabled="isIndexing"
              >
                {{ isIndexing ? 'Indexing...' : 'Index Document' }}
              </button>
            </div>
          </div>

          <!-- Chat Window -->
          <div v-if="selectedDoc" class="chat-container glass-panel">
            <!-- Non Indexed Placeholder -->
            <div v-if="!selectedDoc.indexed" class="chat-placeholder-view">
              <span style="font-size: 3.5rem; display: block; margin-bottom: 16px; opacity: 0.8;">🤖</span>
              <h3 style="font-size: 1.3rem; margin-bottom: 8px;">Document Indexing Required</h3>
              <p style="color: var(--text-muted); max-width: 420px; margin-bottom: 20px;">
                To ask questions about this document, we must chunk, embed, and index the text into our local Chroma Vector Database first.
              </p>
              <button class="btn btn-primary" @click="indexDocument" :disabled="isIndexing">
                {{ isIndexing ? 'Processing Embedding Models...' : 'Index Content Now' }}
              </button>
            </div>

            <!-- Chat window when indexed -->
            <div v-else class="chat-window-inner">
              <div class="chat-messages-scroll" ref="chatScroll">
                <div v-if="!chatHistories[selectedDocId] || chatHistories[selectedDocId].length === 0" class="chat-welcome-box">
                  <h4 style="font-size: 1.1rem; margin-bottom: 6px;">Sentinel AI Q&A Assistant</h4>
                  <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 16px;">
                    Ask questions grounded in the context of <strong>{{ selectedDoc.filename }}</strong>.
                  </p>
                  <div class="suggested-prompts-grid">
                    <button class="suggested-btn" @click="chatQuestion = 'What sensitive PII findings exist in this document?'; submitQuery();">
                      "What sensitive PII findings exist?"
                    </button>
                    <button class="suggested-btn" @click="chatQuestion = 'Provide a brief summary of the document contents.'; submitQuery();">
                      "Summarize this document."
                    </button>
                    <button class="suggested-btn" @click="chatQuestion = 'List any compliance violations or risks.'; submitQuery();">
                      "What compliance risks are identified?"
                    </button>
                  </div>
                </div>

                <div 
                  v-else
                  v-for="(msg, idx) in chatHistories[selectedDocId]" 
                  :key="idx" 
                  class="chat-message-row"
                  :class="[msg.role === 'user' ? 'msg-user' : 'msg-ai']"
                >
                  <div class="msg-avatar">
                    {{ msg.role === 'user' ? '👤' : '🛡️' }}
                  </div>
                  <div class="msg-bubble">
                    <div class="msg-sender-name">{{ msg.role === 'user' ? 'You' : 'Sentinel AI' }}</div>
                    <div class="msg-content">{{ msg.content }}</div>
                  </div>
                </div>

                <div v-if="isQuerying" class="chat-message-row msg-ai">
                  <div class="msg-avatar">🛡️</div>
                  <div class="msg-bubble">
                    <div class="msg-sender-name">Sentinel AI</div>
                    <div class="msg-content"><span class="typing-indicator"><span>•</span><span>•</span><span>•</span></span></div>
                  </div>
                </div>
              </div>

              <!-- Input bar -->
              <div class="chat-input-bar">
                <input 
                  type="text" 
                  v-model="chatQuestion" 
                  placeholder="Ask a question about this document..."
                  @keyup.enter="submitQuery"
                  :disabled="isQuerying"
                  class="chat-textbox"
                />
                <button 
                  class="btn btn-primary" 
                  @click="submitQuery" 
                  :disabled="!chatQuestion.trim() || isQuerying"
                  style="padding: 10px 16px; border-radius: 8px;"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- AUDIT LOG TAB -->
      <section v-if="currentTab === 'audit'" class="tab-content animated">
        <div class="page-header">
          <h1 class="page-title">Audit Trail</h1>
          <p class="page-description">Chronological ledger of security scans, summarization requests, and context queries.</p>
        </div>

        <div class="card glass-panel flex-column" style="gap: 20px;">
          <!-- Search Header -->
          <div style="display: flex; gap: 16px; width: 100%;">
            <input 
              type="text" 
              v-model="auditSearch" 
              placeholder="Search audit trail (by filename, action, or risk level)..."
              class="audit-search-input"
              style="flex-grow: 1;"
            />
            <button class="btn btn-secondary" @click="fetchAuditLogs()">Refresh Logs</button>
          </div>

          <!-- Audit Logs Table -->
          <div v-if="filteredAuditLogs.length === 0" style="padding: 40px; text-align: center; color: var(--text-muted);">
            No audit log entries found matching search query.
          </div>
          <div v-else class="table-container">
            <table class="audit-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Filename</th>
                  <th>Risk Rating</th>
                  <th>Document ID</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(log, idx) in filteredAuditLogs" :key="idx">
                  <td style="font-family: 'Fira Code', monospace; font-size: 0.8rem; white-space: nowrap;">
                    {{ formatDate(log.timestamp) }}
                  </td>
                  <td>
                    <span 
                      class="audit-action-badge"
                      :class="{
                        'action-scan': log.action === 'scan',
                        'action-summary': log.action === 'summary',
                        'action-query': log.action === 'query'
                      }"
                    >
                      {{ log.action }}
                    </span>
                  </td>
                  <td><strong>{{ log.filename }}</strong></td>
                  <td>
                    <span 
                      v-if="log.risk_level"
                      class="badge" 
                      :class="{
                        'badge-high': log.risk_level === 'High',
                        'badge-medium': log.risk_level === 'Medium',
                        'badge-low': log.risk_level === 'Low'
                      }"
                    >
                      {{ log.risk_level }}
                    </span>
                    <span v-else style="color: var(--text-muted); font-size: 0.85rem;">—</span>
                  </td>
                  <td style="font-family: 'Fira Code', monospace; font-size: 0.85rem; color: var(--text-muted);">
                    {{ log.doc_id }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
/* Page Layout adjustments */
.explorer-layout {
  display: flex;
  gap: 24px;
  height: calc(100vh - 170px);
}

.explorer-sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.doc-list-scroll {
  overflow-y: auto;
  flex-grow: 1;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.doc-list-item {
  padding: 14px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
  background: rgba(255, 255, 255, 0.02);
}

.doc-list-item:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--border-color);
}

.doc-list-item.active {
  background: var(--accent-glow);
  border-color: var(--accent-primary);
}

.doc-filename {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-bright);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 170px;
}

.explorer-report-area {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.report-content-flow {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.report-dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

/* Findings Table */
.findings-table, .audit-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}

.findings-table th, .findings-table td, .audit-table th, .audit-table td {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  font-size: 0.9rem;
}

.findings-table th, .audit-table th {
  text-align: left;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.5px;
}

.findings-table tr:hover, .audit-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

/* Code Previews */
.code-preview {
  font-family: 'Fira Code', monospace;
  background: #090b0f;
  color: #c9d1d9;
  padding: 16px;
  border-radius: 8px;
  font-size: 0.85rem;
  overflow-x: auto;
  border: 1px solid var(--border-color);
  white-space: pre-wrap;
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
}

.raw-preview {
  background: rgba(248, 81, 73, 0.02);
  border-color: rgba(248, 81, 73, 0.15);
}

/* Drag and Drop Zone */
.drag-drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s ease;
  background: rgba(255,255,255,0.01);
}

.drag-drop-zone:hover, .drag-drop-zone.active {
  border-color: var(--accent-primary);
  background: var(--accent-glow);
}

.upload-cloud-icon {
  font-size: 2.5rem;
  opacity: 0.6;
}

.file-icon-big {
  font-size: 2.5rem;
  color: var(--accent-primary);
}

/* RAG Chat Assistant styling */
.chat-workspace {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 170px);
}

.chat-container {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
}

.chat-placeholder-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  text-align: center;
  height: 100%;
  box-sizing: border-box;
}

.chat-window-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.chat-messages-scroll {
  flex-grow: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-welcome-box {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  max-width: 600px;
  margin: 40px auto;
}

.suggested-prompts-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.suggested-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-normal);
  padding: 10px 16px;
  border-radius: 8px;
  text-align: left;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s ease;
}

.suggested-btn:hover {
  background: rgba(56, 139, 253, 0.1);
  border-color: var(--accent-primary);
  color: var(--text-bright);
}

.chat-message-row {
  display: flex;
  gap: 16px;
  max-width: 80%;
  animation: fadeIn 0.3s ease;
}

.msg-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.msg-ai {
  align-self: flex-start;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.msg-user .msg-avatar {
  background: var(--accent-glow);
  border-color: var(--accent-primary);
}

.msg-bubble {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 16px;
}

.msg-user .msg-bubble {
  background: #1f6feb;
  color: var(--text-bright);
  border-color: transparent;
}

.msg-sender-name {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.msg-user .msg-sender-name {
  color: rgba(255, 255, 255, 0.7);
  text-align: right;
}

.msg-content {
  font-size: 0.95rem;
  white-space: pre-wrap;
}

.chat-input-bar {
  padding: 16px 24px;
  background: rgba(13, 15, 20, 0.7);
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 12px;
  align-items: center;
}

.chat-textbox {
  flex-grow: 1;
  background: #090b0f;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-normal);
  padding: 12px 16px;
  font-family: inherit;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.2s;
}

.chat-textbox:focus {
  border-color: var(--accent-primary);
}

/* Typing indicator */
.typing-indicator span {
  display: inline-block;
  font-size: 1.5rem;
  line-height: 0.5;
  animation: typing 1s infinite;
  margin: 0 1px;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 100% { opacity: 0.2; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-4px); }
}

/* Form Dropdowns & Search */
.doc-select-dropdown, .audit-search-input {
  background: #090b0f;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-normal);
  padding: 8px 12px;
  outline: none;
  font-family: inherit;
  font-size: 0.9rem;
}

.doc-select-dropdown:focus, .audit-search-input:focus {
  border-color: var(--accent-primary);
}

.table-container {
  overflow-x: auto;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #090b0f;
}

.audit-action-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.action-scan { background: rgba(56, 139, 253, 0.15); color: #58a6ff; }
.action-summary { background: rgba(187, 128, 250, 0.15); color: #bc8cff; }
.action-query { background: rgba(219, 109, 40, 0.15); color: #ff9e64; }

/* Markdown Report formatting */
:deep(.markdown-body) {
  line-height: 1.6;
}

:deep(.summary-h1) {
  font-size: 1.5rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
  margin-top: 24px;
  margin-bottom: 16px;
}

:deep(.summary-h2) {
  font-size: 1.25rem;
  margin-top: 20px;
  margin-bottom: 12px;
}

:deep(.summary-h3) {
  font-size: 1.1rem;
  margin-top: 16px;
  margin-bottom: 8px;
}

:deep(.summary-li) {
  margin-bottom: 8px;
}

:deep(strong) {
  color: var(--text-bright);
}
</style>
