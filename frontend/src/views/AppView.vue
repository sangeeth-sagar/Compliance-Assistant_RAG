<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import api from '../api/client.js'

const router = useRouter()
const auth = useAuthStore()

const currentTab = ref('scan')
const documents = ref([])
const selectedDocId = ref(null)
const selectedDoc = ref(null)
const auditLogs = ref([])
const chatHistories = ref({})

const isScanning = ref(false)
const isSummarizing = ref(false)
const isIndexing = ref(false)
const isQuerying = ref(false)
const globalLoading = ref(false)
const errorMessage = ref('')

const selectedFile = ref(null)
const useSpacy = ref(false)
const dragOver = ref(false)

const chatQuestion = ref('')
const chatScroll = ref(null)
const auditSearch = ref('')

const fetchDocuments = async () => {
  try {
    const res = await api.get('/documents')
    documents.value = res.data
    if (documents.value.length > 0 && !selectedDocId.value) {
      selectedDocId.value = documents.value[documents.value.length - 1].id
    }
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || err.message
  }
}

const fetchDocumentDetails = async (docId) => {
  if (!docId) return
  globalLoading.value = true
  try {
    const res = await api.get(`/documents/${docId}`)
    selectedDoc.value = res.data
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || err.message
  } finally {
    globalLoading.value = false
  }
}

const fetchAuditLogs = async () => {
  try {
    const res = await api.get('/audit')
    auditLogs.value = res.data
  } catch (err) {
    console.error(err)
  }
}

const fetchChatHistory = async (docId) => {
  if (!docId) return
  try {
    const res = await api.get(`/documents/${docId}/chat`)
    chatHistories.value[docId] = res.data.map(m => ({ role: m.role, content: m.content }))
  } catch {
    chatHistories.value[docId] = []
  }
}

watch(selectedDocId, (newId) => {
  if (newId) {
    fetchDocumentDetails(newId)
    fetchChatHistory(newId)
  } else {
    selectedDoc.value = null
  }
})

onMounted(async () => {
  await auth.fetchUser()
  fetchDocuments()
  fetchAuditLogs()
})

const handleFileChange = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
  }
}

const handleDrop = (e) => {
  dragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    const ext = file.name.split('.').pop().toLowerCase()
    if (['pdf', 'txt', 'csv'].includes(ext)) {
      selectedFile.value = file
    }
  }
}

const scanDocument = async () => {
  if (!selectedFile.value) return
  isScanning.value = true
  errorMessage.value = ''

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('use_spacy', useSpacy.value)

  try {
    const res = await api.post('/scan', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    selectedDocId.value = res.data.id
    await fetchDocuments()
    await fetchAuditLogs()
    currentTab.value = 'documents'
    selectedFile.value = null
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || err.message
  } finally {
    isScanning.value = false
  }
}

const generateSummary = async () => {
  if (!selectedDocId.value) return
  isSummarizing.value = true
  errorMessage.value = ''
  try {
    const res = await api.post(`/documents/${selectedDocId.value}/summary`)
    selectedDoc.value = res.data
    await fetchDocuments()
    await fetchAuditLogs()
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || err.message
  } finally {
    isSummarizing.value = false
  }
}

const indexDocument = async () => {
  if (!selectedDocId.value) return
  isIndexing.value = true
  errorMessage.value = ''
  try {
    await api.post(`/documents/${selectedDocId.value}/index`)
    if (selectedDoc.value) selectedDoc.value.indexed = true
    await fetchDocuments()
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || err.message
  } finally {
    isIndexing.value = false
  }
}

const submitQuery = async () => {
  const query = chatQuestion.value.trim()
  if (!query || !selectedDocId.value) return

  if (!chatHistories.value[selectedDocId.value]) {
    chatHistories.value[selectedDocId.value] = []
  }

  chatHistories.value[selectedDocId.value].push({ role: 'user', content: query })
  chatQuestion.value = ''
  isQuerying.value = true
  await nextTick()
  if (chatScroll.value) chatScroll.value.scrollTop = chatScroll.value.scrollHeight

  try {
    const res = await api.post(`/documents/${selectedDocId.value}/query`, { question: query })
    chatHistories.value[selectedDocId.value].push({ role: 'assistant', content: res.data.answer })
    await fetchAuditLogs()
  } catch (err) {
    chatHistories.value[selectedDocId.value].push({
      role: 'assistant',
      content: `Error: ${err.response?.data?.detail || err.message}`,
    })
  } finally {
    isQuerying.value = false
    await nextTick()
    if (chatScroll.value) chatScroll.value.scrollTop = chatScroll.value.scrollHeight
  }
}

const filteredAuditLogs = computed(() => {
  const q = auditSearch.value.toLowerCase().trim()
  if (!q) return auditLogs.value
  return auditLogs.value.filter(log =>
    (log.filename || '').toLowerCase().includes(q) ||
    (log.action || '').toLowerCase().includes(q) ||
    (log.risk_level || '').toLowerCase().includes(q)
  )
})

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatMarkdown = (text) => {
  if (!text) return ''
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/^### (.*$)/gim, '<h4 class="summary-h3">$1</h4>')
  html = html.replace(/^## (.*$)/gim, '<h3 class="summary-h2">$1</h3>')
  html = html.replace(/^# (.*$)/gim, '<h2 class="summary-h1">$1</h2>')
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/^\s*-\s+(.*$)/gim, '<li class="summary-li">$1</li>')
  html = html.replace(/\n/g, '<br>')
  return html
}

const logout = () => {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="app-container">
    <aside class="sidebar">
      <div class="logo-container">
        <span class="nav-icon" style="font-size:1.6rem;color:#58a6ff;">&#x1f6e1;&#xfe0f;</span>
        <div class="logo-text">Compliance Sentinel</div>
      </div>

      <nav class="nav-links">
        <div class="nav-item" :class="{ active: currentTab === 'scan' }" @click="currentTab = 'scan'">
          <span class="nav-icon">&#x1f4e4;</span>
          <span>Scan Document</span>
        </div>
        <div class="nav-item" :class="{ active: currentTab === 'documents' }" @click="currentTab = 'documents'; fetchDocuments();">
          <span class="nav-icon">&#x1f4c2;</span>
          <span>Document Explorer</span>
        </div>
        <div class="nav-item" :class="{ active: currentTab === 'chat' }" @click="currentTab = 'chat'; fetchDocuments();">
          <span class="nav-icon">&#x1f4ac;</span>
          <span>AI Chat / RAG</span>
        </div>
        <div class="nav-item" :class="{ active: currentTab === 'audit' }" @click="currentTab = 'audit'; fetchAuditLogs();">
          <span class="nav-icon">&#x1f4dc;</span>
          <span>Audit Log</span>
        </div>
      </nav>

      <div class="sidebar-footer" style="display:flex;flex-direction:column;gap:8px;">
        <div v-if="auth.user" style="font-size:0.8rem;color:var(--text-normal);">
          {{ auth.user.full_name || auth.user.email }}
        </div>
        <button class="btn btn-secondary" style="width:100%;font-size:0.8rem;padding:6px 12px;" @click="logout">Sign Out</button>
      </div>
    </aside>

    <main class="main-content">
      <div v-if="errorMessage" class="alert alert-info animated" style="margin-bottom:24px;background:rgba(248,81,73,0.1);border-color:rgba(248,81,73,0.2);color:#ff7b72;">
        <span style="font-size:1.2rem;">&#x26a0;&#xfe0f;</span>
        <div style="flex-grow:1;"><strong>Error:</strong> {{ errorMessage }}</div>
        <button @click="errorMessage = ''" style="background:none;border:none;color:inherit;cursor:pointer;font-size:1.1rem;">&times;</button>
      </div>

      <!-- SCAN TAB -->
      <section v-if="currentTab === 'scan'" class="tab-content animated">
        <div class="page-header">
          <h1 class="page-title">Scan New Document</h1>
          <p class="page-description">Upload PDFs, CSVs, or text files to audit risk scoring, redact PII and evaluate compliance.</p>
        </div>
        <div class="grid-2">
          <div class="card glass-panel flex-column" style="gap:20px;">
            <h2 style="font-size:1.25rem;margin-bottom:12px;display:flex;align-items:center;gap:8px;">Select File</h2>
            <div class="drag-drop-zone" :class="{ active: dragOver }" @dragover.prevent="dragOver = true" @dragleave.prevent="dragOver = false" @drop.prevent="handleDrop" @click="$refs.fileInput.click()">
              <input type="file" ref="fileInput" @change="handleFileChange" accept=".pdf,.txt,.csv" style="display:none;" />
              <div v-if="!selectedFile" class="drag-drop-placeholder">
                <p style="font-weight:600;margin:12px 0 6px 0;color:var(--text-bright);">Drag & Drop your document here</p>
                <p style="font-size:0.85rem;color:var(--text-muted);">Supports PDF, TXT, CSV</p>
              </div>
              <div v-else class="selected-file-display">
                <p style="font-weight:600;margin:8px 0 4px 0;color:var(--text-bright);">{{ selectedFile.name }}</p>
                <p style="font-size:0.85rem;color:var(--text-muted);">{{ formatSize(selectedFile.size) }}</p>
              </div>
            </div>
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;">
              <input type="checkbox" v-model="useSpacy" style="transform:scale(1.15);" />
              <span style="font-size:0.85rem;color:var(--text-muted);">Enable spaCy NER</span>
            </label>
            <div style="display:flex;gap:12px;margin-top:10px;">
              <button class="btn btn-primary" style="flex-grow:1;height:48px;" :disabled="!selectedFile || isScanning" @click="scanDocument">
                {{ isScanning ? 'Processing...' : 'Analyze Document' }}
              </button>
              <button v-if="selectedFile" class="btn btn-secondary" @click="selectedFile = null" :disabled="isScanning">Clear</button>
            </div>
          </div>
          <div class="card glass-panel flex-column" style="gap:16px;background:rgba(56,139,253,0.03);">
            <h2 style="font-size:1.25rem;">Security & Privacy Safeguards</h2>
            <ul style="margin:0;padding-left:20px;color:var(--text-muted);display:flex;flex-direction:column;gap:12px;">
              <li><strong>Zero PII Leakage:</strong> Sensitive identifiers redacted locally before indexing or LLM calls.</li>
              <li><strong>Weighted Risk Assessment:</strong> Higher scores for identity docs, PAN, Aadhaar, keys.</li>
              <li><strong>OCR Fallback:</strong> Tesseract for scanned PDFs when text extraction fails.</li>
              <li><strong>Audit Trails:</strong> All actions logged with timestamps.</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- DOCUMENTS TAB -->
      <section v-if="currentTab === 'documents'" class="tab-content animated">
        <div class="page-header">
          <h1 class="page-title">Document Explorer</h1>
          <p class="page-description">Browse scanned documents, examine PII findings, and review compliance summaries.</p>
        </div>
        <div v-if="documents.length === 0" class="card glass-panel text-center" style="padding:60px 24px;">
          <h2 style="font-size:1.5rem;margin-bottom:8px;">No Scanned Documents</h2>
          <p style="color:var(--text-muted);margin-bottom:20px;">Upload a document to get started.</p>
          <button class="btn btn-primary" @click="currentTab = 'scan'">Scan Document</button>
        </div>
        <div v-else class="explorer-layout">
          <div class="explorer-sidebar glass-panel">
            <h2 style="font-size:1.1rem;padding:16px;border-bottom:1px solid var(--border-color);margin:0;">
              Scanned Files ({{ documents.length }})
            </h2>
            <div class="doc-list-scroll">
              <div v-for="doc in documents" :key="doc.id" class="doc-list-item" :class="{ active: selectedDocId === doc.id }" @click="selectedDocId = doc.id">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;width:100%;">
                  <span class="doc-filename" :title="doc.filename">{{ doc.filename }}</span>
                  <span class="badge" :class="{ 'badge-high': doc.risk_level === 'High', 'badge-medium': doc.risk_level === 'Medium', 'badge-low': doc.risk_level === 'Low' }">
                    {{ doc.risk_level }}
                  </span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:0.75rem;color:var(--text-muted);">
                  <span>Score: {{ doc.risk_score }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="explorer-report-area">
            <div v-if="globalLoading" class="card glass-panel text-center" style="padding:100px 24px;">
              <p>Loading document details...</p>
            </div>
            <div v-else-if="selectedDoc" class="report-content-flow animated">
              <div class="report-dashboard-grid">
                <div class="card glass-panel" :style="{ borderLeft: '4px solid ' + (selectedDoc.risk_level === 'High' ? 'var(--risk-high)' : selectedDoc.risk_level === 'Medium' ? 'var(--risk-medium)' : 'var(--risk-low)') }">
                  <div style="font-size:0.85rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;">Risk Classification</div>
                  <div style="display:flex;align-items:baseline;gap:10px;margin-top:12px;">
                    <span style="font-size:2rem;font-weight:800;" :style="{ color: selectedDoc.risk_level === 'High' ? 'var(--risk-high)' : selectedDoc.risk_level === 'Medium' ? 'var(--risk-medium)' : 'var(--risk-low)' }">
                      {{ selectedDoc.risk_level }}
                    </span>
                    <span style="color:var(--text-muted);font-size:1.1rem;">(Score: {{ selectedDoc.risk_score }})</span>
                  </div>
                </div>
                <div class="card glass-panel">
                  <div style="font-size:0.85rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;">RAG Status</div>
                  <div style="margin-top:12px;">
                    <span v-if="selectedDoc.indexed" style="color:var(--risk-low);font-weight:600;">Indexed & Active</span>
                    <span v-else style="color:var(--text-muted);">Not Indexed</span>
                  </div>
                </div>
              </div>
              <div class="grid-2">
                <div class="card glass-panel">
                  <h3 style="font-size:1.1rem;margin-bottom:16px;">PII Findings</h3>
                  <div v-if="!selectedDoc.findings || Object.keys(selectedDoc.findings).length === 0" style="padding:20px;text-align:center;color:var(--text-muted);">
                    No findings detected.
                  </div>
                  <table v-else class="findings-table">
                    <thead><tr><th>Type</th><th style="text-align:center;">Count</th></tr></thead>
                    <tbody>
                      <tr v-for="(count, type) in selectedDoc.findings" :key="type">
                        <td><strong>{{ type }}</strong></td>
                        <td style="text-align:center;">{{ count.length }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="card glass-panel flex-column" style="gap:16px;">
                  <h3 style="font-size:1.1rem;">Compliance Actions</h3>
                  <button class="btn btn-primary" @click="generateSummary" :disabled="isSummarizing" style="width:100%;height:44px;">
                    {{ isSummarizing ? 'Generating...' : (selectedDoc.summary_text ? 'Regenerate Summary' : 'Generate Summary') }}
                  </button>
                  <button v-if="!selectedDoc.indexed" class="btn btn-secondary" @click="indexDocument" :disabled="isIndexing" style="width:100%;height:44px;">
                    {{ isIndexing ? 'Indexing...' : 'Index for Q&A' }}
                  </button>
                  <button v-else class="btn btn-secondary" @click="currentTab = 'chat'" style="width:100%;height:44px;">
                    Open in AI Chat
                  </button>
                </div>
              </div>
              <div v-if="selectedDoc.summary_text" class="card glass-panel animated" style="border-left:4px solid var(--accent-primary);">
                <h3 style="font-size:1.2rem;margin-bottom:16px;">AI Compliance Report</h3>
                <div class="markdown-body" v-html="formatMarkdown(selectedDoc.summary_text)"></div>
              </div>
              <div class="card glass-panel">
                <h3 style="font-size:1.1rem;margin-bottom:16px;">Document Content</h3>
                <div style="display:flex;flex-direction:column;gap:20px;">
                  <div>
                    <h4 style="font-size:0.95rem;color:var(--text-muted);margin-bottom:8px;">Redacted Content</h4>
                    <pre class="code-preview">{{ (selectedDoc.redacted_text || '').slice(0, 3000) }}</pre>
                  </div>
                  <div>
                    <h4 style="font-size:0.95rem;color:var(--text-muted);margin-bottom:8px;">Raw Content</h4>
                    <pre class="code-preview raw-preview">{{ (selectedDoc.raw_text || '').slice(0, 1000) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- CHAT TAB -->
      <section v-if="currentTab === 'chat'" class="tab-content animated">
        <div class="page-header">
          <h1 class="page-title">AI Chat Assistant (RAG)</h1>
          <p class="page-description">Ask questions about document content. Conversation history is preserved.</p>
        </div>
        <div v-if="documents.length === 0" class="card glass-panel text-center" style="padding:60px 24px;">
          <h2>No Documents Yet</h2>
          <p style="color:var(--text-muted);margin-bottom:20px;">Scan a document first.</p>
          <button class="btn btn-primary" @click="currentTab = 'scan'">Scan Document</button>
        </div>
        <div v-else class="chat-workspace">
          <div class="card glass-panel" style="padding:16px;display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:12px;flex-grow:1;">
              <span style="font-weight:600;font-size:0.95rem;">Document:</span>
              <select v-model="selectedDocId" class="doc-select-dropdown" style="flex-grow:1;max-width:400px;">
                <option v-for="doc in documents" :key="doc.id" :value="doc.id">{{ doc.filename }}</option>
              </select>
            </div>
            <div v-if="selectedDoc">
              <span v-if="selectedDoc.indexed" class="badge badge-low" style="height:24px;">RAG Ready</span>
              <button v-else class="btn btn-primary" style="height:32px;padding:0 16px;font-size:0.8rem;" @click="indexDocument" :disabled="isIndexing">
                {{ isIndexing ? 'Indexing...' : 'Index Document' }}
              </button>
            </div>
          </div>
          <div v-if="selectedDoc" class="chat-container glass-panel">
            <div v-if="!selectedDoc.indexed" class="chat-placeholder-view">
              <h3>Document Indexing Required</h3>
              <p style="color:var(--text-muted);margin-bottom:20px;">Index the document first to enable Q&A.</p>
              <button class="btn btn-primary" @click="indexDocument" :disabled="isIndexing">
                {{ isIndexing ? 'Processing...' : 'Index Now' }}
              </button>
            </div>
            <div v-else class="chat-window-inner">
              <div class="chat-messages-scroll" ref="chatScroll">
                <div v-if="!chatHistories[selectedDocId] || chatHistories[selectedDocId].length === 0" class="chat-welcome-box">
                  <h4>Sentinel AI Q&A Assistant</h4>
                  <p style="color:var(--text-muted);font-size:0.9rem;">Ask questions about <strong>{{ selectedDoc.filename }}</strong>.</p>
                </div>
                <div v-else v-for="(msg, idx) in chatHistories[selectedDocId]" :key="idx" class="chat-message-row" :class="[msg.role === 'user' ? 'msg-user' : 'msg-ai']">
                  <div class="msg-avatar">{{ msg.role === 'user' ? '&#x1f464;' : '&#x1f6e1;&#xfe0f;' }}</div>
                  <div class="msg-bubble">
                    <div class="msg-sender-name">{{ msg.role === 'user' ? 'You' : 'Sentinel AI' }}</div>
                    <div class="msg-content">{{ msg.content }}</div>
                  </div>
                </div>
                <div v-if="isQuerying" class="chat-message-row msg-ai">
                  <div class="msg-avatar">&#x1f6e1;&#xfe0f;</div>
                  <div class="msg-bubble">
                    <div class="msg-sender-name">Sentinel AI</div>
                    <div class="msg-content"><span class="typing-indicator"><span>&bull;</span><span>&bull;</span><span>&bull;</span></span></div>
                  </div>
                </div>
              </div>
              <div class="chat-input-bar">
                <input type="text" v-model="chatQuestion" placeholder="Ask a question..." @keyup.enter="submitQuery" :disabled="isQuerying" class="chat-textbox" />
                <button class="btn btn-primary" @click="submitQuery" :disabled="!chatQuestion.trim() || isQuerying" style="padding:10px 16px;border-radius:8px;">Send</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- AUDIT TAB -->
      <section v-if="currentTab === 'audit'" class="tab-content animated">
        <div class="page-header">
          <h1 class="page-title">Audit Trail</h1>
          <p class="page-description">Chronological ledger of all actions.</p>
        </div>
        <div class="card glass-panel flex-column" style="gap:20px;">
          <div style="display:flex;gap:16px;width:100%;">
            <input type="text" v-model="auditSearch" placeholder="Search audit trail..." class="audit-search-input" style="flex-grow:1;" />
            <button class="btn btn-secondary" @click="fetchAuditLogs()">Refresh</button>
          </div>
          <div v-if="filteredAuditLogs.length === 0" style="text-align:center;padding:40px;color:var(--text-muted);">
            No audit entries found.
          </div>
          <table v-else class="audit-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Filename</th>
                <th>Risk</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in filteredAuditLogs" :key="log.id">
                <td>{{ formatDate(log.created_at) }}</td>
                <td><span class="badge badge-low">{{ log.action }}</span></td>
                <td>{{ log.filename || '-' }}</td>
                <td>{{ log.risk_level || '-' }}</td>
                <td>{{ log.details ? JSON.stringify(log.details) : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.flex-column { display: flex; flex-direction: column; }
.text-center { text-align: center; }
.drag-drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}
.drag-drop-zone:hover, .drag-drop-zone.active {
  border-color: var(--accent-primary);
  background: var(--accent-glow);
}
.drag-drop-placeholder p { margin: 4px 0; }
.explorer-layout { display: grid; grid-template-columns: 280px 1fr; gap: 24px; }
.explorer-sidebar { border-radius: 12px; overflow: hidden; max-height: calc(100vh - 180px); overflow-y: auto; }
.doc-list-scroll { display: flex; flex-direction: column; }
.doc-list-item { padding: 14px 16px; border-bottom: 1px solid var(--border-color); cursor: pointer; transition: background 0.15s; }
.doc-list-item:hover { background: rgba(255,255,255,0.03); }
.doc-list-item.active { background: var(--accent-glow); border-left: 3px solid var(--accent-primary); }
.doc-filename { font-weight: 600; font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.report-dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
.findings-table { width: 100%; border-collapse: collapse; }
.findings-table th, .findings-table td { padding: 8px 12px; border-bottom: 1px solid var(--border-color); text-align: left; font-size: 0.85rem; }
.code-preview { background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; font-family: 'Fira Code', monospace; font-size: 0.8rem; white-space: pre-wrap; max-height: 300px; overflow-y: auto; color: var(--text-normal); }
.raw-preview { color: var(--risk-high); opacity: 0.8; }
.chat-workspace { display: flex; flex-direction: column; height: calc(100vh - 180px); }
.chat-container { display: flex; flex-direction: column; flex-grow: 1; overflow: hidden; }
.chat-window-inner { display: flex; flex-direction: column; flex-grow: 1; overflow: hidden; }
.chat-messages-scroll { flex-grow: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.chat-welcome-box { text-align: center; padding: 40px; margin: auto; }
.chat-message-row { display: flex; gap: 12px; max-width: 85%; }
.msg-user { margin-left: auto; flex-direction: row-reverse; }
.msg-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-tertiary); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; flex-shrink: 0; }
.msg-bubble { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 12px 16px; }
.msg-user .msg-bubble { background: var(--accent-glow); border-color: rgba(47,129,247,0.3); }
.msg-sender-name { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); margin-bottom: 4px; }
.msg-content { font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap; }
.chat-input-bar { display: flex; gap: 8px; padding: 16px; border-top: 1px solid var(--border-color); }
.chat-textbox { flex-grow: 1; padding: 10px 14px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-normal); font-size: 0.9rem; outline: none; }
.chat-textbox:focus { border-color: var(--accent-primary); }
.typing-indicator span { animation: blink 1.4s infinite both; font-size: 1.2rem; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,80%,100% { opacity: 0.2; } 40% { opacity: 1; } }
.audit-search-input { padding: 10px 14px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-normal); font-size: 0.9rem; outline: none; }
.audit-table { width: 100%; border-collapse: collapse; }
.audit-table th, .audit-table td { padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: left; font-size: 0.85rem; }
.audit-table th { color: var(--text-muted); text-transform: uppercase; font-size: 0.75rem; font-weight: 600; }
.doc-select-dropdown { padding: 8px 12px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-normal); font-size: 0.9rem; }
.markdown-body { font-size: 0.9rem; line-height: 1.6; color: var(--text-normal); }
</style>
