/**
 * 道藏天阁 - 道藏详情页
 * 路径：subpackages/jingzang/resource-detail/resource-detail
 */
const { get, post } = require('../../../utils/request');

Page({
  data: {
    resourceId: '',
    resource: null,
    comments: [],
    loading: true,
    loadingComments: false,
    commentText: '',
  },

  onLoad(options) {
    if (!options.id) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }
    this.setData({ resourceId: options.id });
    this.loadDetail();
    this.loadComments();
  },

  async loadDetail() {
    this.setData({ loading: true });
    try {
      const res = await get(`/resources/${this.data.resourceId}`);
      this.setData({ resource: res, loading: false });
    } catch (e) {
      console.error('[道藏详情] 加载失败', e);
      this.setData({ resource: null, loading: false });
    }
  },

  async loadComments() {
    this.setData({ loadingComments: true });
    try {
      const res = await get(`/resources/${this.data.resourceId}/comments`);
      this.setData({ comments: res.comments || res.items || [], loadingComments: false });
    } catch (e) {
      console.error('[道藏详情] 加载评论失败', e);
      this.setData({ loadingComments: false });
    }
  },

  onCommentInput(e) {
    this.setData({ commentText: e.detail.value });
  },

  async onSubmitComment() {
    const text = this.data.commentText.trim();
    if (!text) {
      wx.showToast({ title: '请输入评论内容', icon: 'none' });
      return;
    }
    try {
      await post(`/resources/${this.data.resourceId}/comments`, { content: text });
      this.setData({ commentText: '' });
      wx.showToast({ title: '评论成功', icon: 'success' });
      this.loadComments();
    } catch (e) {
      wx.showToast({ title: '评论失败', icon: 'none' });
    }
  },

  async onLike() {
    if (!this.data.resource) return;
    try {
      await post(`/resources/${this.data.resourceId}/like`);
      const resource = this.data.resource;
      this.setData({
        resource: {
          ...resource,
          likes: resource.is_liked ? (resource.likes || 1) - 1 : (resource.likes || 0) + 1,
          is_liked: !resource.is_liked,
        },
      });
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  async onFavorite() {
    if (!this.data.resource) return;
    const action = this.data.resource.is_favorited ? 'remove' : 'add';
    try {
      await post(`/resources/${this.data.resourceId}/favorite?action=${action}`);
      const resource = this.data.resource;
      this.setData({ resource: { ...resource, is_favorited: !resource.is_favorited } });
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  scrollToComments() {
    wx.pageScrollTo({ selector: '#comments', duration: 300 });
  },

  onShare() {
    const { resource } = this.data;
    if (!resource) return;
    wx.showShareMenu({ withShareTicket: true });
  },

  onShareAppMessage() {
    const { resource } = this.data;
    return {
      title: resource ? `📖 ${resource.title}` : '📖 道藏天阁',
      path: `/subpackages/jingzang/resource-detail/resource-detail?id=${this.data.resourceId}`,
    };
  },

  onBack() {
    wx.navigateBack();
  },
});
