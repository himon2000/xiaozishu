/**
 * 评价页面
 * 路径: pages/review/review
 */
const { get, post } = require('../../utils/request');

Page({
  data: {
    orderId: '',
    serviceTitle: '',
    providerNickname: '',
    rating: 5,
    tags: [],
    tagSet: {},      // { [tagName]: true } 用于 WXML 快速判断选中状态
    availableTags: [],
    content: '',
    images: [],
    anonymous: false,
    submitting: false,
  },

  onLoad(options) {
    if (options.order_id) {
      this.setData({ orderId: options.order_id });
      this.loadReviewTags();
    }
    if (options.title) {
      this.setData({ serviceTitle: decodeURIComponent(options.title) });
    }
    if (options.provider) {
      this.setData({ providerNickname: decodeURIComponent(options.provider) });
    }
  },

  async loadReviewTags() {
    try {
      const res = await get('/reviews/tags');
      this.setData({ availableTags: res.tags });
    } catch (e) {
      console.error('加载评价标签失败', e);
    }
  },

  // 评分
  onRatingTap(e) {
    const rating = parseInt(e.currentTarget.dataset.rating);
    this.setData({ rating });
  },

  // 标签选择
  onTagTap(e) {
    const tag = e.currentTarget.dataset.tag;
    const tags = this.data.tags.slice();
    const tagSet = Object.assign({}, this.data.tagSet);
    const index = tags.indexOf(tag);
    if (index > -1) {
      tags.splice(index, 1);
      delete tagSet[tag];
    } else if (tags.length < 5) {
      tags.push(tag);
      tagSet[tag] = true;
    }
    this.setData({ tags, tagSet });
  },

  // 内容输入
  onContentInput(e) {
    this.setData({ content: e.detail.value });
  },

  // 匿名开关
  onAnonymousChange(e) {
    this.setData({ anonymous: e.detail.value.length > 0 });
  },

  // 添加图片
  onAddImage() {
    if (this.data.images.length >= 9) {
      wx.showToast({ title: '最多9张图片', icon: 'none' });
      return;
    }
    wx.chooseMedia({
      count: 9 - this.data.images.length,
      mediaType: ['image'],
      success: (res) => {
        const newImages = res.tempFiles.map(f => f.tempFilePath);
        this.setData({
          images: [...this.data.images, ...newImages].slice(0, 9)
        });
      },
    });
  },

  // 删除图片
  onRemoveImage(e) {
    const index = e.currentTarget.dataset.index;
    const images = this.data.images;
    images.splice(index, 1);
    this.setData({ images });
  },

  // 提交评价
  async onSubmit() {
    const { orderId, rating, content, tags, images, anonymous, submitting } = this.data;

    if (submitting) return;

    if (!content.trim()) {
      wx.showToast({ title: '请输入评价内容', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    wx.showLoading({ title: '提交中...' });

    try {
      // TODO: 上传图片获取URL
      const imageUrls = [];

      await post('/reviews', {
        order_id: orderId,
        rating,
        content,
        tags,
        images: imageUrls,
        anonymous,
      });

      wx.hideLoading();
      wx.showToast({ title: '评价成功！', icon: 'success' });

      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: e.detail || '提交失败', icon: 'none' });
      this.setData({ submitting: false });
    }
  },
});
