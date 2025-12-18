<template>
  <MainLayout>
    <div class="h-full flex flex-col" style="background-color: var(--color-bg-primary)">
      <!-- Header (match DataUploadView/RAGManagementView tone) -->
      <div class="bg-white border-b px-6 py-4" style="border-color: var(--color-border-light)">
        <div class="max-w-6xl mx-auto">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h1 class="text-2xl font-bold" style="color: var(--color-gray-900)">관리</h1>
              <p class="mt-1" style="color: var(--color-gray-600)">
                `qdrant_embedding_docs/` 문서를 임베딩/인덱싱해서 RAG 근거(출처) 기반 답변을 준비합니다.
              </p>
            </div>

            <button
              @click="refreshHealth"
              :disabled="isCheckingHealth"
              class="inline-flex items-center px-4 py-2 bg-white text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors duration-200 shadow-sm border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              style="min-width: 160px;"
              title="상태 새로고침"
            >
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v6h6M20 20v-6h-6M5 19a9 9 0 0014-7 9 9 0 00-14-7" />
              </svg>
              <span class="text-sm">{{ isCheckingHealth ? "확인 중..." : "상태 새로고침" }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto">
        <div class="max-w-6xl mx-auto p-6 space-y-6">
          <!-- Stats cards (like RAGManagementView) -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-white rounded-xl shadow-md border-0 p-4 hover:shadow-lg transition-shadow duration-200">
              <div class="flex items-center">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center bg-blue-600">
                  <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V7a2 2 0 00-2-2H6a2 2 0 00-2 2v6m16 0a2 2 0 01-2 2H6a2 2 0 01-2-2m16 0l-4-4m-8 0l-4 4" />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-xs font-medium text-gray-600">Qdrant 연결</p>
                  <p class="text-xl font-bold text-gray-900">
                    {{ ragOk ? "OK" : "X" }}
                  </p>
                </div>
              </div>
              <div class="mt-2">
                <span
                  :class="[
                    'px-2 py-1 text-xs rounded-full font-medium',
                    ragOk ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  ]"
                >
                  {{ ragOk ? "연결됨" : "미연결" }}
                </span>
              </div>
            </div>

            <div class="bg-white rounded-xl shadow-md border-0 p-4 hover:shadow-lg transition-shadow duration-200">
              <div class="flex items-center">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center bg-green-600">
                  <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-xs font-medium text-gray-600">Embeddings 설정</p>
                  <p class="text-xl font-bold text-gray-900">
                    {{ embeddingsOk ? "OK" : "CHECK" }}
                  </p>
                </div>
              </div>
              <div class="mt-2">
                <span
                  :class="[
                    'px-2 py-1 text-xs rounded-full font-medium',
                    embeddingsOk ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  ]"
                >
                  {{ embeddingsOk ? "준비됨" : "확인 필요" }}
                </span>
              </div>
            </div>

            <div class="bg-white rounded-xl shadow-md border-0 p-4 hover:shadow-lg transition-shadow duration-200">
              <div class="flex items-center">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center bg-yellow-500">
                  <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </div>
                <div class="ml-3 min-w-0">
                  <p class="text-xs font-medium text-gray-600">컬렉션</p>
                  <p class="text-sm font-bold text-gray-900 truncate">
                    {{ runtimeConfig?.qdrant_collection || "-" }}
                  </p>
                </div>
              </div>
              <p class="text-xs text-gray-500 mt-2 font-mono break-all">rag: {{ ragBaseUrlLabel }}</p>
            </div>

            <div class="bg-white rounded-xl shadow-md border-0 p-4 hover:shadow-lg transition-shadow duration-200">
              <div class="flex items-center">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center bg-blue-600">
                  <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div class="ml-3 min-w-0">
                  <p class="text-xs font-medium text-gray-600">임베딩(목표)</p>
                  <p class="text-xl font-bold text-gray-900">
                    {{ runtimeConfig?.expected_vector_dim || "-" }}
                  </p>
                </div>
              </div>
              <p class="text-xs text-gray-500 mt-2 font-mono break-all">
                deploy: {{ runtimeConfig?.azure_embedding_deployment || "-" }}
              </p>
            </div>
          </div>

          <!-- Health error -->
          <div v-if="ragHealthError" class="bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="flex items-center">
              <svg class="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p class="text-red-800 font-medium">상태 확인 실패</p>
            </div>
            <p class="text-red-600 text-sm mt-1 whitespace-pre-wrap">{{ ragHealthError }}</p>
          </div>

          <!-- Main -->
          <div class="grid grid-cols-1 gap-6">
            <!-- Action -->
            <div class="bg-white rounded-xl shadow-md border-0 overflow-hidden">
              <div class="p-6">
                <div class="text-center mb-6">
                  <h2 class="text-2xl font-bold mb-2 text-gray-900">문서 임베딩</h2>
                  <p class="text-gray-600 text-sm">qdrant_embedding_docs → chunk → embedding → Qdrant upsert</p>
                </div>

                <button
                  @click="runIndexing"
                  :disabled="isRunning"
                  class="w-full inline-flex items-center justify-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors duration-200 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  style="border: 1px solid #2563eb;"
                >
                  <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                  </svg>
                  {{ isRunning ? "임베딩 실행 중..." : "임베딩 실행" }}
                </button>

                <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
                  <div class="flex items-center">
                    <svg class="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <p class="text-red-800 font-medium">실행 실패</p>
                  </div>
                  <p class="text-red-600 text-sm mt-1 whitespace-pre-wrap">{{ error }}</p>
                </div>

                <div v-if="result" class="mt-4">
                  <div class="text-xs font-medium text-gray-700 mb-2">결과</div>
                  <pre class="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto max-h-56">{{ result }}</pre>
                </div>

                <div v-if="preview && preview.length" class="mt-5">
                  <div class="flex items-center justify-between mb-2">
                    <div class="text-xs font-medium text-gray-700">청킹 미리보기</div>
                    <div class="text-xs text-gray-500">파일 {{ preview.length }}개(샘플)</div>
                  </div>

                  <!-- prevent page from getting too long: scroll inside this box -->
                  <div class="space-y-3 max-h-80 overflow-y-auto pr-1">
                    <div
                      v-for="(p, idx) in preview"
                      :key="p.source || idx"
                      class="border border-gray-200 rounded-lg overflow-hidden"
                    >
                      <button
                        class="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors"
                        @click="togglePreviewOpen(idx)"
                      >
                        <div class="min-w-0 text-left">
                          <div class="text-xs font-mono text-gray-700 break-all">{{ p.source }}</div>
                          <div class="text-xs text-gray-500 mt-0.5">chunks: {{ p.chunk_count }}</div>
                        </div>
                        <svg
                          class="w-4 h-4 text-gray-400 transition-transform duration-200 flex-shrink-0"
                          :class="previewOpen[idx] ? 'rotate-180' : ''"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>

                      <div v-if="previewOpen[idx]" class="p-3 bg-white">
                        <div class="space-y-2">
                          <div
                            v-for="(c, cidx) in (p.sample_chunks || [])"
                            :key="cidx"
                            class="rounded-lg border border-gray-200 bg-gray-50 p-3"
                          >
                            <div class="text-[11px] text-gray-500 mb-1">chunk {{ cidx + 1 }} · chars {{ c.chars }}</div>
                            <div class="text-xs text-gray-800 whitespace-pre-wrap max-h-40 overflow-y-auto pr-1">{{ c.preview }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import MainLayout from "@/components/layout/MainLayout.vue";
import { ref, onMounted } from "vue";
import { checkRagHealth, indexQdrantEmbeddingDocs } from "@/utils/api";
import apiConfig from "@/config/api";

const isRunning = ref(false);
const error = ref("");
const result = ref("");
const ragOk = ref(false);
const embeddingsOk = ref(false);
const ragHealthError = ref("");
const isCheckingHealth = ref(false);
const ragBaseUrlLabel = ref("");
const runtimeConfig = ref(null);
const preview = ref([]);
const previewOpen = ref([]);

const togglePreviewOpen = (idx) => {
  previewOpen.value[idx] = !previewOpen.value[idx];
};

const refreshHealth = async () => {
  isCheckingHealth.value = true;
  ragHealthError.value = "";
  try {
    const h = await checkRagHealth();
    ragOk.value = Boolean(h?.qdrant_ok);
    embeddingsOk.value = Boolean(h?.embeddings_configured);
    runtimeConfig.value = h?.runtime_config || null;
  } catch (e) {
    ragOk.value = false;
    embeddingsOk.value = false;
    ragHealthError.value = e?.message || "rag-service health 확인 실패";
    runtimeConfig.value = null;
  } finally {
    isCheckingHealth.value = false;
  }
};

const runIndexing = async () => {
  isRunning.value = true;
  error.value = "";
  result.value = "";
  preview.value = [];
  previewOpen.value = [];
  try {
    const res = await indexQdrantEmbeddingDocs({ maxFiles: 200, recreate: false });
    result.value = JSON.stringify(res, null, 2);
    preview.value = Array.isArray(res?.preview) ? res.preview : [];
    previewOpen.value = preview.value.map(() => false);
  } catch (e) {
    error.value = e?.message || "임베딩 실행 중 오류가 발생했습니다.";
  } finally {
    isRunning.value = false;
  }
};

onMounted(() => {
  try {
    ragBaseUrlLabel.value = apiConfig?.ENDPOINTS?.RAG_HEALTH?.replace(/\/health$/, "") || "http://localhost:8005";
  } catch {
    ragBaseUrlLabel.value = "http://localhost:8005";
  }
  refreshHealth();
});
</script>


