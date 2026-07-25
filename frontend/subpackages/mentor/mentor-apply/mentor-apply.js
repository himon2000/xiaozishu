/**
 * 道友传承模块 - 申请传承页面
 * 路径：subpackages/mentor/mentor-apply/mentor-apply
 */
const { get, post } = require('../../../utils/request');

Page({
  data: {
    mentorOpenid: '',
    mentor: null,
    message: '',
    // 道友传承新增字段
    mentorType: 'academic',   // 'enterprise' | 'academic'
    mentorDirection: 'academic', // 'employment' | 'academic'
    submitting: false,
  },

  onLoad(options) {
    if (!options.openid) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }
    const mentorType = options.mentor_type || 'academic';
    const mentorDirection = mentorType === 'enterprise' ? 'employment' : 'academic';
    this.setData({
      mentorOpenid: options.openid,
      mentorType,
      mentorDirection,
    });
    this.loadMentorInfo();
  },

  async loadMentorInfo() {
    try {
      const res = await get('/mentorships/mentors', {
        page: 1,
        page_size: 50,
        mentor_type: this.data.mentorType,
      });
      const mentors = res.mentors || [];
      const mentor = mentors.find(m => m.openid === this.data.mentorOpenid);
      this.setData({ mentor: mentor || null });
    } catch (e) {
      console.error('[申请传承] 加载失败', e);
    }
  },

  onMessageInput(e) {
    this.setData({ message: e.detail.value });
  },

  async onSubmit() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      const result = await post('/mentorships/apply', {
        mentor_openid: this.data.mentorOpenid,
        message: this.data.message.trim(),
        mentor_type: this.data.mentorType,
        mentor_direction: this.data.mentorDirection,
      });
      wx.showToast({ title: result.message || '申请成功', icon: 'success' });
      setTimeout(() => wx.navigateBack(), 1500);
    } catch (e) {
      wx.showToast({ title: e.message || '申请失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },

  onBack() {
    wx.navigateBack();
  },
});
