const { get } = require('../../utils/request');

Page({
  data: {
    user: null,

    // 统计数据
    stats: {
      total: 0,
      ongoing: 0,
      published: 0,
      cited: 0,
    },

    // 课题列表
    researchList: [],

    // 当前标签
    currentTab: 'ongoing',

    // 空状态提示
    emptyTips: {
      ongoing: '暂无进行中的课题',
      published: '暂无已发表的课题',
      all: '您还没有发布任何课题',
    },
  },

  onLoad() {
    this.loadData();
  },

  async loadData() {
    try {
      // 模拟数据（实际应从API获取）
      const researchList = [
        {
          id: 1,
          title: '基于深度学习的校园垃圾分类研究',
          status: 'ongoing',
          statusText: '进行中',
          progress: 60,
          deadline: '2026-06-30',
          members: 4,
          comments: 12,
          author: { name: '张三', avatar: '' },
        },
        {
          id: 2,
          title: '大学生创新创业模式研究',
          status: 'published',
          statusText: '已发表',
          journal: '教育现代化',
          publishDate: '2026-03-15',
          citations: 5,
          views: 328,
          author: { name: '张三', avatar: '' },
        },
      ];

      const stats = {
        total: 2,
        ongoing: 1,
        published: 1,
        cited: 5,
      };

      this.setData({
        researchList,
        stats,
      });
    } catch (e) {
      console.error('加载课题数据失败', e);
    }
  },

  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ currentTab: tab });
  },

  onResearchTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.showToast({ title: '课题详情开发中', icon: 'none' });
  },

  onPublishResearch() {
    wx.navigateTo({ url: '/pages/team-plaza/team-plaza?action=create&category=research' });
  },

  getFilteredList() {
    if (this.data.currentTab === 'all') {
      return this.data.researchList;
    }
    return this.data.researchList.filter(item => item.status === this.data.currentTab);
  },

  onShareAppMessage() {
    return {
      title: '查看我的学术课题研究成果！',
      path: '/pages/home/home',
    };
  },
});
