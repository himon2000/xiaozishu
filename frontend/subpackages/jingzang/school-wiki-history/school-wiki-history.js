/**
 * 道藏天阁 - 高校百科问答历史
 * 路径：subpackages/jingzang/school-wiki-history/school-wiki-history
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    history: [],
    loading: true,
    historyError: '',
  },

  onLoad() {
    this.loadHistory();
  },

  async loadHistory() {
    this.setData({ loading: true, historyError: '' });
    try {
      const res = await get('/school-wiki/history');
      const data = res.data || res;
      const list = data.records || data.history || [];
      this.setData({ history: list, loading: false });
    } catch (e) {
      console.error('[问答历史] 加载失败', e);
      this.setData({ loading: false, historyError: e.message || e.detail || '历史读取失败，点击重试' });
    }
  },

  onBack() {
    wx.navigateBack();
  },

  onCopySource(e) {
    const url = e.currentTarget.dataset.url;
    if (typeof url === 'string' && /^https:\/\//i.test(url)) wx.setClipboardData({ data: url });
  },
});
