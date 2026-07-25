/**
 * 道友传承模块 - 传承树页面
 * 路径：subpackages/mentor/lineage-tree/lineage-tree
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    tree: null,
    loading: true,
    mentorshipId: '',
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ mentorshipId: options.id });
      this.loadLineage(options.id);
    } else {
      // 没有指定传承关系，加载我的道友传承
      this.loadMyMentorships();
    }
  },

  async loadMyMentorships() {
    try {
      const res = await get('/mentorships/mine');
      // 优先看作为被传承者的传承
      const asDisciple = res.as_disciple && res.as_disciple[0];
      if (asDisciple) {
        this.setData({ mentorshipId: asDisciple.id });
        this.loadLineage(asDisciple.id);
      } else {
        this.setData({ tree: null, loading: false });
      }
    } catch (e) {
      console.error('[传承树] 加载失败', e);
      this.setData({ loading: false });
    }
  },

  async loadLineage(id) {
    this.setData({ loading: true });
    try {
      const res = await get(`/mentorships/${id}/lineage`);
      this.setData({ tree: res, loading: false });
    } catch (e) {
      console.error('[传承树] 加载失败', e);
      this.setData({ loading: false });
    }
  },

  onFindMentor() {
    wx.navigateTo({ url: '/subpackages/mentor/find-mentor/find-mentor' });
  },

  onBack() {
    wx.navigateBack();
  },
});
