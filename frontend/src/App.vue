<template>
  <main>
    <h1>光伏组串IV扫描台</h1>
    <div v-if="!session">
      <p class="sub">扫描员提交开路电压、短路电流与填充因子；通知通道叫醒工人出结论。登录框已预填可写账号 scanner / scan123456。</p>
      <section>
        <label>用户名</label><input v-model="loginUser" autocomplete="off" />
        <label>密码</label><input type="password" v-model="loginPass" autocomplete="off" />
        <button :disabled="loading" @click="login">登录</button>
        <p v-if="error" class="err">{{ error }}</p>
      </section>
    </div>
    <div v-else>
      <p class="sub">已登录：{{ session.username }}（{{ isWriter ? "可提交" : "只读观察员" }}）</p>
      <section>
        <button class="secondary" @click="logout">退出</button>
        <button class="secondary" @click="refresh">刷新列表</button>
      </section>

      <section v-if="isWriter">
        <h2>提交扫描</h2>
        <label>组串编号</label><input v-model="stringCode" placeholder="例如 阵列C-串05" />
        <label>开路电压 V</label><input type="number" step="0.1" v-model="voc" />
        <label>短路电流 A</label><input type="number" step="0.1" v-model="isc" />
        <label>填充因子</label><input type="number" step="0.01" v-model="ff" />
        <button :disabled="loading" @click="submit">提交扫描</button>
        <p v-if="error" class="err">{{ error }}</p>
      </section>
      <section v-else class="notice">
        观察员账号仅可查看排队和结论，不能提交或修改扫描记录。
      </section>

      <section>
        <h2>排队中（{{ pendingLogs.length }}）</h2>
        <table>
          <thead>
            <tr><th>编号</th><th>组串</th><th>Voc</th><th>Isc</th><th>FF</th><th>提交人</th><th>提交时间</th><th>状态</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in pendingLogs" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.string_code }}</td>
              <td>{{ formatNumber(row.voc_v, 2) }} V</td>
              <td>{{ formatNumber(row.isc_a, 2) }} A</td>
              <td>{{ formatNumber(row.fill_factor, 2) }}</td>
              <td>{{ row.created_by }}</td>
              <td>{{ formatTime(row.created_at) }}</td>
              <td><span class="tag pending">待判定</span></td>
            </tr>
            <tr v-if="pendingLogs.length === 0">
              <td colspan="8" class="empty">排队栏为空：当前没有等待判定的扫描。</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h2>已完成（{{ completedLogs.length }}）</h2>
        <table>
          <thead>
            <tr><th>编号</th><th>组串</th><th>Voc</th><th>Isc</th><th>FF</th><th>状态</th><th>结论</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in completedLogs" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.string_code }}</td>
              <td>{{ formatNumber(row.voc_v, 2) }} V</td>
              <td>{{ formatNumber(row.isc_a, 2) }} A</td>
              <td>{{ formatNumber(row.fill_factor, 2) }}</td>
              <td><span class="tag ok">已完成</span></td>
              <td><span class="tag" :class="row.verdict === '合格' ? 'ok' : 'bad'">{{ row.verdict }}</span></td>
              <td><button class="secondary small" @click="openDetail(row.id)">详情</button></td>
            </tr>
            <tr v-if="completedLogs.length === 0">
              <td colspan="8" class="empty">暂无已完成记录。</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <div v-if="selectedLog" class="modal-backdrop" @click.self="closeDetail">
      <section class="modal" role="dialog" aria-modal="true" aria-label="扫描详情">
        <div class="modal-head">
          <h2>扫描详情 #{{ selectedLog.id }}</h2>
          <button class="secondary small" @click="closeDetail">关闭</button>
        </div>
        <dl class="details">
          <div><dt>组串编号</dt><dd>{{ selectedLog.string_code }}</dd></div>
          <div><dt>开路电压 Voc</dt><dd>{{ formatNumber(selectedLog.voc_v, 2) }} V</dd></div>
          <div><dt>短路电流 Isc</dt><dd>{{ formatNumber(selectedLog.isc_a, 2) }} A</dd></div>
          <div><dt>填充因子 FF</dt><dd>{{ formatNumber(selectedLog.fill_factor, 2) }}</dd></div>
          <div><dt>状态</dt><dd>{{ selectedLog.status === 'done' ? '已完成' : '待判定' }}</dd></div>
          <div>
            <dt>结论</dt>
            <dd>
              <span v-if="selectedLog.verdict" class="tag" :class="selectedLog.verdict === '合格' ? 'ok' : 'bad'">{{ selectedLog.verdict }}</span>
              <span v-else>等待判定</span>
            </dd>
          </div>
          <div><dt>判定原因</dt><dd>{{ selectedLog.reason || '工人尚未完成判定' }}</dd></div>
          <div><dt>提交人</dt><dd>{{ selectedLog.created_by }}</dd></div>
          <div><dt>提交时间</dt><dd>{{ formatTime(selectedLog.created_at) }}</dd></div>
          <div><dt>处理时间</dt><dd>{{ formatTime(selectedLog.processed_at) || '—' }}</dd></div>
        </dl>
      </section>
    </div>
  </main>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
const session = ref(null);
const logs = ref([]);
const loginUser = ref("scanner");
const loginPass = ref("scan123456");
const stringCode = ref("");
const voc = ref("");
const isc = ref("");
const ff = ref("");
const error = ref("");
const loading = ref(false);
const selectedLog = ref(null);
let timer;
const isWriter = computed(() => session.value?.role === "writer");
const pendingLogs = computed(() => logs.value.filter(row => row.status === "pending"));
const completedLogs = computed(() => logs.value.filter(row => row.status === "done"));

function headers() {
  return session.value ? { Authorization: "Bearer " + session.value.token } : {};
}
function formatNumber(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "—";
}
function formatTime(value) {
  if (!value) return "";
  const time = new Date(value);
  return Number.isNaN(time.getTime()) ? String(value) : time.toLocaleString("zh-CN", { hour12: false });
}
async function refresh() {
  if (!session.value) return;
  try {
    const res = await fetch("/api/logs", { headers: headers() });
    if (res.status === 401) { logout(); return; }
    if (!res.ok) return;
    logs.value = await res.json();
    if (selectedLog.value) {
      const latest = logs.value.find(row => row.id === selectedLog.value.id);
      if (latest) selectedLog.value = latest;
    }
  } catch {
    // 保留已有列表和详情，下一次轮询自动重试。
  }
}
async function login() {
  error.value = "";
  loading.value = true;
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: loginUser.value, password: loginPass.value }),
    });
    const data = await res.json();
    if (!res.ok) { error.value = data.detail || "登录失败"; return; }
    session.value = { token: data.access_token, username: data.username, role: data.role };
    localStorage.setItem("pv_session", JSON.stringify(session.value));
    await refresh();
    timer = setInterval(refresh, 2000);
  } catch { error.value = "无法连接接口"; }
  finally { loading.value = false; }
}
function logout() {
  if (timer) clearInterval(timer);
  session.value = null;
  logs.value = [];
  selectedLog.value = null;
  localStorage.removeItem("pv_session");
}
async function submit() {
  error.value = "";
  loading.value = true;
  try {
    const res = await fetch("/api/logs", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers() },
      body: JSON.stringify({
        string_code: stringCode.value,
        voc_v: Number(voc.value),
        isc_a: Number(isc.value),
        fill_factor: Number(ff.value),
      }),
    });
    const data = await res.json();
    if (!res.ok) { error.value = data.detail || "提交失败"; return; }
    stringCode.value = voc.value = isc.value = ff.value = "";
    await refresh();
  } catch { error.value = "提交时网络异常"; }
  finally { loading.value = false; }
}
async function openDetail(id) {
  selectedLog.value = logs.value.find(row => row.id === id) || { id };
  try {
    const res = await fetch(`/api/logs/${id}`, { headers: headers() });
    if (res.status === 401) { logout(); return; }
    if (res.ok) selectedLog.value = await res.json();
  } catch {
    // 列表里已有完整读数时仍可打开详情；下次刷新会同步最新结论。
  }
}
function closeDetail() {
  selectedLog.value = null;
}
onMounted(() => {
  const raw = localStorage.getItem("pv_session");
  if (raw) {
    try {
      session.value = JSON.parse(raw);
      refresh();
      timer = setInterval(refresh, 2000);
    } catch { localStorage.removeItem("pv_session"); }
  }
});
onUnmounted(() => { if (timer) clearInterval(timer); });
</script>
<style>
body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; background: #052e16; color: #ecfdf5; }
main { max-width: 1080px; margin: 0 auto; padding: 1.5rem; }
h1 { color: #86efac; margin: 0 0 0.25rem; }
h2 { color: #bbf7d0; margin: 0 0 0.9rem; font-size: 1.05rem; }
.sub { color: #a7f3d0; margin-bottom: 1.25rem; }
section { background: #14532d; border: 1px solid #166534; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
.notice { color: #fde68a; background: #422006; border-color: #854d0e; }
label { display: block; font-size: 0.85rem; margin-bottom: 0.25rem; }
input { width: 100%; box-sizing: border-box; padding: 0.5rem 0.65rem; border-radius: 6px; border: 1px solid #4ade80; background: #022c22; color: #ecfdf5; margin-bottom: 0.75rem; }
button { cursor: pointer; padding: 0.5rem 1rem; border: none; border-radius: 6px; background: #16a34a; color: #fff; font-weight: 600; margin-right: 0.4rem; }
button.secondary { background: #365314; }
button.small { padding: 0.25rem 0.6rem; font-size: 0.82rem; }
.err { color: #fecaca; }
.empty { color: #a7f3d0; text-align: center; padding: 1rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.45rem; border-bottom: 1px solid #166534; }
.tag { display: inline-block; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.8rem; }
.ok { background: #14532d; color: #bbf7d0; }
.bad { background: #7f1d1d; color: #fecaca; }
.pending { background: #854d0e; color: #fde68a; }
.modal-backdrop { position: fixed; inset: 0; background: rgb(0 0 0 / 55%); display: flex; align-items: center; justify-content: center; padding: 1rem; }
.modal { width: min(620px, 100%); background: #14532d; box-shadow: 0 20px 60px rgb(0 0 0 / 45%); margin: 0; }
.modal-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.details { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem 1.2rem; margin: 0; }
.details div { border-bottom: 1px solid #166534; padding-bottom: 0.55rem; }
.details dt { color: #a7f3d0; font-size: 0.8rem; margin-bottom: 0.2rem; }
.details dd { margin: 0; font-weight: 600; }
@media (max-width: 720px) { .details { grid-template-columns: 1fr; } }
</style>
