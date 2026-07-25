/**
 * 道藏天阁 - 高校百科问答历史
 * 路径：subpackages/jingzang/school-wiki-history/school-wiki-history
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    history: [],
    loading: true,
  },

  onLoad() {
    this.loadHistory();
  },

  async loadHistory() {
    this.setData({ loading: true });
    try {
      const res = await get('/school-wiki/history');
      const list = res.history || res.data && res.data.history || [];
      this.setData({ history: list, loading: false });
    } catch (e) {
      console.error('[问答历史] 加载失败', e);
      this.setData({ loading: false });
    }
  },

  onBack() {
    wx.navigateBack();
  },
});
