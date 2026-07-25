/**
 * 下山历练 - 我的机会管理
 * 路径: pages/my-opportunities/my-opportunities
 */
const { get, post } = require('../../utils/request');

Page({
  data: {
    activeTab: 'published', // published|applied|favorites
    published: [],
    applied: [],
    favorites: [],
    page: 1,
    pageSize: 20,
    loading: false,
    noMore: false,
  },

  onLoad(options) {
    if (options.tab) {
      this.setData({ activeTab: options.tab });
    }
    this.loadData();
  },

  onShow() {
    this.loadData(true);
  },

  onPullDownRefresh() {
    this.loadData(true).then(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    this.loadData();
  },

  // 切换标签
  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab, page: 1, noMore: false });
    this.loadData(true);
  },

  // 加载数据
  async loadData(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, noMore: false, published: [], applied: [], favorites: [] });
    }
    if (this.data.noMore) return;

    this.setData({ loading: true });

    try {
      switch (this.data.activeTab) {
        case 'published':
          await this.loadPublished();
          break;
        case 'applied':
          await this.loadApplied();
          break;
        case 'favorites':
          await this.loadFavorites();
          break;
      }
    } catch (e) {
      console.error('加载数据失败', e);
    }

    this.setData({ loading: false });
  },

  // 加载我发布的
  async loadPublished() {
    const res = await get('/opportunities/mine', { page: this.data.page, page_size: this.data.pageSize });
    const list = this.data.page === 1 ? res.opportunities : [...this.data.published, ...res.opportunities];
    this.setData({
      published: list,
      page: this.data.page + 1,
      noMore: list.length >= res.total,
    });
  },

  // 加载我申请的
  async loadApplied() {
    const res = await get('/opportunities/applications/mine', { page: this.data.page, page_size: this.data.pageSize });
    const list = this.data.page === 1 ? res.applications : [...this.data.applied, ...res.applications];
    this.setData({
      applied: list,
      page: this.data.page + 1,
      noMore: list.length >= res.total,
    });
  },

  // 加载我收藏的
  async loadFavorites() {
    const res = await get('/opportunities/favorites/mine', { page: this.data.page, page_size: this.data.pageSize });
    const list = this.data.page === 1 ? res.favorites : [...this.data.favorites, ...res.favorites];
    this.setData({
      favorites: list,
      page: this.data.page + 1,
      noMore: list.length >= res.total,
    });
  },

  // 点击资源卡片
  onOpportunityTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/opportunity-detail/opportunity-detail?id=${id}` });
  },

  // 取消收藏
  async onToggleFavorite(e) {
    const { id } = e.currentTarget.dataset;
    const { favorites } = this.data;
    const index = favorites.findIndex(o => o.id === id);
    if (index === -1) return;

    try {
      const res = await post(`/opportunities/${id}/favorite`);
      if (!res.is_favorited) {
        // 从列表中移除
        const updated = [...favorites];
        updated.splice(index, 1);
        this.setData({ favorites: updated });
        wx.showToast({ title: '已取消收藏', icon: 'success' });
      }
    } catch (e) {
      wx.showToast({ title: e.detail || '操作失败', icon: 'none' });
    }
  },

  // 撤回申请
  async onWithdrawApplication(e) {
    const { id } = e.currentTarget.dataset;
    wx.showModal({
      title: '确认撤回',
      content: '确定要撤回该申请吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await post(`/opportunities/applications/${id}/withdraw`);
            wx.showToast({ title: '已撤回', icon: 'success' });
            this.loadData(true);
          } catch (e) {
            wx.showToast({ title: e.detail || '撤回失败', icon: 'none' });
          }
        }
      }
    });
  },

  // 删除发布的资源
  async onDeleteOpportunity(e) {
    const { id } = e.currentTarget.dataset;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除该资源吗？此操作不可撤销！',
      success: async (res) => {
        if (res.confirm) {
          try {
            await post(`/opportunities/${id}/delete`);
            wx.showToast({ title: '已删除', icon: 'success' });
            this.loadData(true);
          } catch (e) {
            wx.showToast({ title: e.detail || '删除失败', icon: 'none' });
          }
        }
      }
    });
  },
});
