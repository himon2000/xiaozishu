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
    quickQuestions: [
      '复旦大学的录取分数',
      '上交的王牌专业',
      '清华的校园环境',
      '北大的留学项目',
    ],
  },

  onLoad() {
    this.loadSchools();
  },

  async loadSchools() {
    try {
      const res = await get('/school-wiki/schools');
      const list = res.data && res.data.schools ? res.data.schools : res.schools || [];
      this.setData({ schools: list });
    } catch (e) {
      console.error('[万宗宝鉴] 加载学校列表失败', e);
    }
  },

  onSelectSchool(e) {
    const { name } = e.currentTarget.dataset;
    this.setData({ selectedSchool: this.data.selectedSchool === name ? '' : name });
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

      const answer = res.answer || res.data && res.data.answer || '抱歉，暂未找到相关信息。';
      const now = new Date();
      const timeStr = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;

      this.setData({
        messages: [
          ...messages,
          { role: 'ai', content: answer, time: timeStr },
        ],
        loading: false,
      });
    } catch (e) {
      console.error('[万宗宝鉴] 问答失败', e);
      this.setData({
        messages: [
          ...messages,
          { role: 'ai', content: '抱歉，服务暂时不可用，请稍后重试。', time: '' },
        ],
        loading: false,
      });
    }
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
