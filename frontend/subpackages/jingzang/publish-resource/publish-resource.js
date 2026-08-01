/**
 * 道藏天阁 - 发布道藏页面
 * 路径：subpackages/jingzang/publish-resource/publish-resource
 */
const { post } = require('../../../utils/request');
const { uploadImage } = require('../../../utils/upload');
const { ensurePrivacyAuthorized } = require('../../../utils/privacy');

Page({
  data: {
    submitting: false,
    formData: {
      title: '',
      category: '',
      cover_image: '',
      content: '',
      tags: '',
      access_mode: 'free',
      points_price: '',
    },
    categories: [
      { id: 'notes', label: '笔记', icon: '📝' },
      { id: 'guide', label: '攻略', icon: '📖' },
      { id: 'material', label: '资料', icon: '📚' },
      { id: 'template', label: '模板', icon: '📋' },
      { id: 'video', label: '视频', icon: '🎬' },
      { id: 'other', label: '其他', icon: '📦' },
    ],
  },

  onLoad(options) {
    // 预填分类
    if (options.category) {
      this.setData({ 'formData.category': options.category });
    }
  },

  // 标题输入
  onTitleInput(e) {
    this.setData({ 'formData.title': e.detail.value });
  },

  // 分类选择
  onCategorySelect(e) {
    const { id } = e.currentTarget.dataset;
    this.setData({ 'formData.category': id });
  },

  // 选择封面图
  async onChooseCover() {
    try {
      await ensurePrivacyAuthorized();
    } catch (error) {
      return;
    }
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sizeType: ['compressed'],
      success: (res) => {
        const filePath = res.tempFiles[0].tempFilePath;
        this.setData({ 'formData.cover_image': filePath });
      },
      fail: () => {
        wx.showToast({ title: '请重新选择', icon: 'none' });
      },
    });
  },

  // 删除封面
  onRemoveCover() {
    this.setData({ 'formData.cover_image': '' });
  },

  // 内容输入
  onContentInput(e) {
    this.setData({ 'formData.content': e.detail.value });
  },

  // 标签输入
  onTagsInput(e) {
    this.setData({ 'formData.tags': e.detail.value });
  },

  // 快捷标签
  onAppendTag(e) {
    const { tag } = e.currentTarget.dataset;
    const current = this.data.formData.tags;
    const newTags = current ? `${current},${tag}` : tag;
    this.setData({ 'formData.tags': newTags });
  },

  // 获取方式选择
  onAccessSelect(e) {
    const { mode } = e.currentTarget.dataset;
    this.setData({ 'formData.access_mode': mode });
  },

  // 灵石价格输入
  onPointsInput(e) {
    const val = parseInt(e.detail.value, 10);
    if (val > 100) {
      this.setData({ 'formData.points_price': '100' });
    } else {
      this.setData({ 'formData.points_price': e.detail.value });
    }
  },

  // 提交
  async onSubmit() {
    const { formData } = this.data;

    // 验证必填项
    if (!formData.title || formData.title.trim().length < 3) {
      wx.showToast({ title: '请填写标题（至少3个字）', icon: 'none' });
      return;
    }
    if (!formData.category) {
      wx.showToast({ title: '请选择分类', icon: 'none' });
      return;
    }
    if (!formData.content || formData.content.trim().length < 10) {
      wx.showToast({ title: '请填写详细内容（至少10个字）', icon: 'none' });
      return;
    }
    if (formData.access_mode === 'points') {
      const price = parseInt(formData.points_price, 10);
      if (!price || price < 1) {
        wx.showToast({ title: '请设置灵石价格（1-10000）', icon: 'none' });
        return;
      }
    }

    this.setData({ submitting: true });

    try {
      const payload = {
        title: formData.title.trim(),
        resource_type: formData.category,
        content: formData.content.trim(),
        access_mode: formData.access_mode,
      };

      if (formData.cover_image) {
        payload.cover_image = await uploadImage(formData.cover_image, 'resource-covers');
      }
      if (formData.tags) {
        // 将逗号分隔的标签转为数组
        payload.tags = formData.tags
          .split(/[,，]/)
          .map(t => t.trim())
          .filter(t => t.length > 0);
      }
      if (formData.access_mode === 'points' && formData.points_price) {
        payload.points_cost = parseInt(formData.points_price, 10);
      }

      await post('/resources', payload);

      wx.showToast({ title: '发布成功', icon: 'success' });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    } catch (err) {
      console.error('[发布道藏] 失败', err);
      wx.showToast({ title: err.message || '发布失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
