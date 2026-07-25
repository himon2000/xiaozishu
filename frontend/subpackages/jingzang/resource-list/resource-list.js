/**
 * 道藏天阁 - 资源列表/广场/我的发布/我的收藏
 * 路径：subpackages/jingzang/resource-list/resource-list
 */
const { get, post } = require('../../../utils/request');
const app = getApp();

Page({
  data: {
    view: 'square',  // 'square' | 'mine' | 'favorites'
    category: '',
    search: '',
    resources: [],
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    noMore: false,
    hasLoadedOnce: false,
    categories: [
      { id: '', label: '全部' },
      { id: 'notes', label: '📝 学习笔记' },
      { id: 'guide', label: '📖 经验攻略' },
      { id: 'material', label: '📚 复习资料' },
      { id: 'template', label: '📋 模板范本' },
      { id: 'video', label: '🎬 视频课程' },
      { id: 'other', label: '📦 其他' },
    ],
  },

  onLoad(options) {
    // 支持外部传入 view 参数：view=mine, view=favorites
    if (options.view === 'mine') {
      this.setData({ view: 'mine' });
    } else if (options.view === 'favorites') {
      this.setData({ view: 'favorites' });
    }
    if (options.category) {
      this.setData({ category: options.category });
    }
    this.loadResources(true);
  },

  onShow() {
    // 从发布/详情页返回时刷新，保证新发布记录立即可见。
    if (this.data.hasLoadedOnce) {
      this.loadResources(true);
    }
  },

  async loadResources(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, resources: [], noMore: false });
    }
    if (this.data.noMore) return;

    this.setData({ loading: true });
    try {
      let res;
      if (this.data.view === 'mine') {
        res = await get('/resources/mine', {
          page: this.data.page,
          page_size: this.data.pageSize,
        }).catch(() => null);
      } else if (this.data.view === 'favorites') {
        res = await get('/resources/favorites', {
          page: this.data.page,
          page_size: this.data.pageSize,
        }).catch(() => null);
      } else {
        // square - 资源广场
        const params = {
          page: this.data.page,
          page_size: this.data.pageSize,
        };
        if (this.data.category) params.resource_type = this.data.category;
        if (this.data.search) params.keyword = this.data.search;
        res = await get('/resources', params).catch(() => null);
      }

      if (!res) {
        this.setData({ loading: false });
        return;
      }

      const rawList = res.resources || res.items || [];
      // 预处理 shortDesc，避免 WXML 中调用 .slice()
      const processed = rawList.map(item => ({
        ...item,
        shortDesc: item.description
          ? (item.description.length > 60 ? item.description.substring(0, 60) + '...' : item.description)
          : '',
      }));
      const list = reset
        ? processed
        : [...this.data.resources, ...processed];
      const total = res.total || list.length;

      this.setData({
        resources: list,
        total,
        page: this.data.page + 1,
        noMore: list.length >= total,
        loading: false,
        hasLoadedOnce: true,
      });
    } catch (e) {
      console.error('[道藏天阁] 加载失败', e);
      this.setData({ loading: false });
    }
  },

  onReachBottom() {
    this.loadResources();
  },

  onPullDownRefresh() {
    this.loadResources(true).then(() => wx.stopPullDownRefresh());
  },

  // 切换视图
  onViewChange(e) {
    const { view } = e.currentTarget.dataset;
    this.setData({ view, category: '', search: '' });
    this.loadResources(true);
  },

  // 分类切换
  onCategoryChange(e) {
    const { id } = e.currentTarget.dataset;
    this.setData({ category: id });
    this.loadResources(true);
  },

  // 搜索
  onSearchInput(e) {
    this.setData({ search: e.detail.value });
  },

  onSearch(e) {
    this.setData({ search: e.detail.value || this.data.search });
    this.loadResources(true);
  },

  // 点击资源卡片
  onResourceTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/subpackages/jingzang/resource-detail/resource-detail?id=${id}`,
    });
  },

  // 发布资源
  onPublish() {
    wx.navigateTo({
      url: '/subpackages/jingzang/publish-resource/publish-resource',
    });
  },

  // 收藏/取消收藏
  async onToggleFavorite(e) {
    const { id, liked } = e.currentTarget.dataset;
    try {
      if (liked) {
        await post(`/resources/${id}/favorite?action=remove`);
      } else {
        await post(`/resources/${id}/favorite?action=add`);
      }
      // 更新本地状态
      const resources = this.data.resources.map(r => {
        if (r.id === id) {
          return { ...r, likes: liked ? r.likes - 1 : r.likes + 1, is_favorited: !liked };
        }
        return r;
      });
      this.setData({ resources });
    } catch (err) {
      console.error('[道藏天阁] 收藏失败', err);
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  onShareAppMessage() {
    return {
      title: '📖 道藏天阁 - 小紫薯道藏天阁',
      path: '/subpackages/jingzang/resource-list/resource-list',
    };
  },
});
