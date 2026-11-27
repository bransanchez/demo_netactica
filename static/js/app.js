/**
 * Netactica Monitor - Frontend Vue 3 Application
 * Maneja eventos Server-Sent Events (SSE), estado de pasos, tabla de peticiones,
 * reproductor de video del proceso y lightbox de screenshots.
 */

const { createApp, ref, computed, nextTick, onMounted, onUnmounted } = Vue;

const app = createApp({
    setup() {
        // --- Estado reactivo ---
        const connected = ref(false);
        const isRunning = ref(false);
        const runningFlow = ref(null);
        const steps = ref([]);
        const requests = ref([]);
        const requestMap = ref({});
        const infoLines = ref([]);
        const expandedReq = ref(null);
        const recording = ref(false);
        const videoUrl = ref(null);
        const infoLogRef = ref(null);

        // Modal Lightbox
        const lightbox = ref({
            open: false,
            src: '',
            title: '',
            stepIndex: 0
        });

        const MAX_INFO = 300;

        // --- Computed ---
        const completedSteps = computed(() =>
            steps.value.filter(s => s.status === 'ok').length
        );

        const sortedRequests = computed(() =>
            [...requests.value].reverse()
        );

        // --- Métodos de utilidad y etiquetas ---
        function statusLabel(status) {
            const labels = {
                pending: 'Pendiente',
                running: 'En ejecución',
                ok: 'Completado',
                error: 'Error'
            };
            return labels[status] || status;
        }

        function stateLabel(state) {
            const labels = {
                pending: 'En curso',
                done: 'Completa',
                failed: 'Error'
            };
            return labels[state] || state;
        }

        function truncateUrl(url) {
            return url && url.length > 80 ? url.substring(0, 80) + '...' : url;
        }

        function toggleDetail(id) {
            expandedReq.value = expandedReq.value === id ? null : id;
        }

        function formatDetail(req) {
            return [
                `URL: ${req.url}`,
                `Método: ${req.method}`,
                `Tipo: ${req.rtype || '—'}`,
                `Estado: ${stateLabel(req.state)}`,
                `Status: ${req.status ?? 'Pendiente'}`,
                `Tiempo: ${req.time_ms != null ? req.time_ms + ' ms' : 'Pendiente'}`,
                `Tamaño: ${req.size != null ? req.size + ' bytes' : 'Pendiente'}`,
                `MIME: ${req.mime || '—'}`,
                '',
                'Request headers:',
                JSON.stringify(req.req_headers || {}, null, 2),
                '',
                'Payload:',
                req.post_data || 'No disponible',
                '',
                'Response headers:',
                JSON.stringify(req.res_headers || {}, null, 2),
                '',
                'Response body:',
                req.body || 'No disponible',
                req.error ? `\nError: ${req.error}` : ''
            ].join('\n');
        }

        function addInfoLine(message, ts) {
            const time = new Date((ts || Date.now() / 1000) * 1000).toLocaleTimeString();
            infoLines.value.push({ time, message });
            if (infoLines.value.length > MAX_INFO) {
                infoLines.value.splice(0, infoLines.value.length - MAX_INFO);
            }
            nextTick(() => {
                if (infoLogRef.value) {
                    infoLogRef.value.scrollTop = infoLogRef.value.scrollHeight;
                }
            });
        }

        function identifyFlow(stepNames) {
            if (stepNames.includes('Buscar vuelos (aéreo)')) return 'Aéreo';
            if (stepNames.includes('Buscar hoteles')) return 'Hotel';
            return null;
        }

        function startFlow(endpoint, flowName) {
            isRunning.value = true;
            runningFlow.value = flowName;
            videoUrl.value = null;

            fetch(endpoint, { method: 'POST' })
                .then(async res => {
                    const result = await res.json();
                    if (!res.ok) throw new Error(result.error || `HTTP ${res.status}`);
                })
                .catch(err => {
                    addInfoLine(`No se pudo iniciar ${flowName}: ${err.message}`);
                    isRunning.value = false;
                    runningFlow.value = null;
                });
        }

        // --- Lightbox ---
        function openLightbox(stepIndex) {
            const step = steps.value[stepIndex];
            if (!step || !step.screenshot) return;
            lightbox.value = {
                open: true,
                src: 'data:image/png;base64,' + step.screenshot,
                title: `Paso ${stepIndex + 1}: ${step.name}`,
                stepIndex
            };
        }

        function closeLightbox() {
            lightbox.value.open = false;
        }

        function navigateLightbox(dir) {
            if (!lightbox.value.open) return;
            let idx = lightbox.value.stepIndex + dir;
            while (idx >= 0 && idx < steps.value.length) {
                if (steps.value[idx].screenshot) {
                    openLightbox(idx);
                    return;
                }
                idx += dir;
            }
        }

        function handleKeydown(e) {
            if (!lightbox.value.open) return;
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowLeft') navigateLightbox(-1);
            if (e.key === 'ArrowRight') navigateLightbox(1);
        }

        // --- Lucide Icons Refresh ---
        function refreshIcons() {
            nextTick(() => {
                if (window.lucide && typeof window.lucide.createIcons === 'function') {
                    window.lucide.createIcons();
                }
            });
        }

        // --- SSE (Server-Sent Events) ---
        let evtSource = null;

        function connectSSE() {
            evtSource = new EventSource('/stream');

            evtSource.onopen = () => {
                connected.value = true;
                refreshIcons();
            };

            evtSource.onerror = () => {
                connected.value = false;
                refreshIcons();
            };

            evtSource.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'reset') {
                    const flow = identifyFlow(data.steps);
                    if (flow) {
                        runningFlow.value = flow;
                        isRunning.value = true;
                    }
                    steps.value = data.steps.map(name => ({
                        name,
                        status: 'pending',
                        screenshot: null,
                        error: null
                    }));
                    requests.value = [];
                    requestMap.value = {};
                    infoLines.value = [];
                    videoUrl.value = null;
                    refreshIcons();
                }

                if (data.type === 'step') {
                    const step = steps.value[data.index];
                    if (step) {
                        step.status = data.status;
                        if (data.screenshot) step.screenshot = data.screenshot;
                        if (data.error) step.error = data.error;
                    }
                    refreshIcons();
                }

                if (data.type === 'info') {
                    addInfoLine(data.message, data.ts);
                }

                if (data.type === 'done') {
                    const flow = runningFlow.value;
                    isRunning.value = false;
                    runningFlow.value = null;
                    if (!data.ok) {
                        addInfoLine(`Flujo ${flow || ''} finalizó con error.`);
                    } else {
                        addInfoLine(`Flujo ${flow || ''} completado exitosamente.`);
                    }
                    refreshIcons();
                }

                if (data.type === 'recording_started') {
                    recording.value = true;
                    addInfoLine('Grabación de video iniciada.');
                    refreshIcons();
                }

                if (data.type === 'recording_stopped') {
                    recording.value = false;
                    if (data.video_url) {
                        videoUrl.value = data.video_url;
                        addInfoLine('Grabación de video finalizada. Video disponible.');
                    }
                    refreshIcons();
                }

                if (data.type === 'net') {
                    const existing = requestMap.value[data.id];
                    if (existing) {
                        Object.assign(existing, data);
                    } else {
                        const req = { ...data };
                        requestMap.value[data.id] = req;
                        requests.value.push(req);
                    }
                }
            };
        }

        // --- Lifecycle ---
        onMounted(() => {
            connectSSE();
            document.addEventListener('keydown', handleKeydown);
            refreshIcons();
        });

        onUnmounted(() => {
            if (evtSource) evtSource.close();
            document.removeEventListener('keydown', handleKeydown);
        });

        return {
            connected,
            isRunning,
            runningFlow,
            steps,
            requests,
            infoLines,
            expandedReq,
            recording,
            videoUrl,
            lightbox,
            infoLogRef,
            completedSteps,
            sortedRequests,
            statusLabel,
            stateLabel,
            truncateUrl,
            toggleDetail,
            formatDetail,
            startFlow,
            openLightbox,
            closeLightbox,
            refreshIcons
        };
    }
});

app.mount('#app');
