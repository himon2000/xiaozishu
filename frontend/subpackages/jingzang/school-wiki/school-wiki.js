/**
 * 道藏天阁 - 高校百科 AI 问答
 * 路径：subpackages/jingzang/school-wiki/school-wiki
 */
const { get, post } = require('../../../utils/request');

Page({
  data: {
    schools: [],
    selectedSchool: '',
    inputText: '',
    messages: [],
    loading: false,
    schoolError: '',
    graphVersion: '',
    knowledge: [],
    knowledgeSources: [],
    knowledgeLoading: false,
    knowledgeError: '',
    topic: 'all',
    topics: [
      { id: 'all', label: '综合知识' },
      { id: 'admissions', label: '招生择校' },
      { id: 'teaching', label: '教学知识' },
      { id: 'research', label: '科研知识' },
    ],
    showKnowledge: false,
    quickQuestions: [
      '数据科学与大数据技术有哪些课程？',
      '2026年广东综合评价有哪些专业？',
      '数据科学学院有哪些公开科研项目？',
    ],
  },

  onLoad() {
    this.loadSchools();
  },

  async loadSchools() {
    try {
      const res = await get('/school-wiki/schools');
      const list = res.data && res.data.schools ? res.data.schools : res.schools || [];
      const data = res.data || res;
      const selected = list.some(s => s.name === this.data.selectedSchool) ? this.data.selectedSchool : (list[0] && list[0].name) || '';
      this.setData({ schools: list, selectedSchool: selected, schoolError: '', graphVersion: data.graph_version || '' });
    } catch (e) {
      console.error('[万宗宝鉴] 加载学校列表失败', e);
      this.setData({ schoolError: e.message || e.detail || '知识图谱服务暂不可用，点击重试' });
    }
  },

  onSelectSchool(e) {
    const { name } = e.currentTarget.dataset;
    this.setData({ selectedSchool: name, knowledge: [], knowledgeSources: [] });
    if (this.data.showKnowledge) this.loadKnowledge();
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  async onAsk() {
    const text = this.data.inputText.trim();
    if (!text || this.data.loading) return;

    // 添加用户消息
    const messages = [...this.data.messages, { role: 'user', content: text }];
    this.setData({ messages, inputText: '', loading: true });

    try {
      const res = await post('/school-wiki/ask', {
        question: text,
        school_name: this.data.selectedSchool,
      });

      const data = res.data || res;
      const answer = data.answer || '暂未找到已核验的相关信息。';
      const now = new Date();
      const timeStr = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;

      this.setData({
        messages: [
          ...messages,
          { role: 'ai', content: answer, time: timeStr, sources: data.sources || [],
            caveats: data.caveats || [], evidenceStatus: data.evidence_status,
            graphVersion: data.graph_version || '',
            historyWarning: data.history_saved === false ? '游客问答或历史未保存；登录后可查看已保存记录。' : '' },
        ],
        loading: false,
      });
    } catch (e) {
      console.error('[万宗宝鉴] 问答失败', e);
      this.setData({
        messages: [
          ...messages,
          { role: 'ai', content: e.message || e.detail || '知识图谱服务暂时不可用，请稍后重试。', time: '' },
        ],
        loading: false,
      });
    }
  },

  onToggleKnowledge() {
    const show = !this.data.showKnowledge;
    this.setData({ showKnowledge: show });
    if (show) this.loadKnowledge();
  },

  onTopic(e) {
    this.setData({ topic: e.currentTarget.dataset.id });
    this.loadKnowledge();
  },

  async loadKnowledge() {
    if (!this.data.selectedSchool) return;
    const school = this.data.selectedSchool;
    const topic = this.data.topic;
    this.setData({ knowledgeLoading: true, knowledgeError: '' });
    try {
      const res = await get('/school-wiki/knowledge', { school_name: school, topic });
      if (school !== this.data.selectedSchool || topic !== this.data.topic) return;
      const data = res.data || res;
      this.setData({ knowledge: data.nodes || [], knowledgeSources: data.sources || [], knowledgeLoading: false });
    } catch (e) {
      if (school !== this.data.selectedSchool || topic !== this.data.topic) return;
      this.setData({ knowledge: [], knowledgeSources: [], knowledgeLoading: false,
        knowledgeError: e.message || e.detail || '图谱读取失败，点击重试' });
    }
  },

  onCopySource(e) {
    const url = e.currentTarget.dataset.url;
    if (typeof url !== 'string' || !/^https:\/\//i.test(url)) return;
    wx.setClipboardData({ data: url });
  },

  onQuickQuestion(e) {
    const { q } = e.currentTarget.dataset;
    this.setData({ inputText: q });
    this.onAsk();
  },

  onShowHistory() {
    wx.navigateTo({
      url: '/subpackages/jingzang/school-wiki-history/school-wiki-history',
    });
  },

  onBack() {
    wx.navigateBack();
  },

  onShareAppMessage() {
    return {
      title: '🎓 万宗宝鉴 - 小紫薯高校百科',
      path: '/subpackages/jingzang/school-wiki/school-wiki',
    };
  },

  onPublishRequest() {
    // 发布高校相关需求，跳转到服务发布页（带高校/志愿标签）
    wx.navigateTo({
      url: '/subpackages/jingzang/publish-resource/publish-resource?category=zong_men',
    });
  },
});
