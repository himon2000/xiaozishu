/**
 * 道友传承模块 - 我的道友页面
 * 路径：subpackages/mentor/my-disciples/my-disciples
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    tab: 'disciples',
    disciples: [],   // 我指导的弟子（导师视角）
    mentors: [],     // 我的导师（被传承者视角）
    loading: false,
  },

  onLoad() {
    this.loadMyMentorships();
  },

  async loadMyMentorships() {
    this.setData({ loading: true });
    try {
      const res = await get('/mentorships/mine');
      this.setData({
        disciples: res.as_mentor || [],     // 作为导师指导的弟子
        mentors: res.as_disciple || [],     // 我的导师
        loading: false,
      });
    } catch (e) {
      console.error('[我的道友] 加载失败', e);
      this.setData({ loading: false });
    }
  },

  onTabChange(e) {
    this.setData({ tab: e.currentTarget.dataset.tab });
  },

  onViewTree(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/subpackages/mentor/lineage-tree/lineage-tree?id=${id}` });
  },

  onBack() {
    wx.navigateBack();
  },

  onShareAppMessage() {
    return {
      title: '🎓 我的道友传承 - 小紫薯道途同契',
      path: '/subpackages/mentor/my-disciples/my-disciples',
    };
  },
});
