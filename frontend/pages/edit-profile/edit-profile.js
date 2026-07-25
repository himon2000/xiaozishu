/**
 * 编辑个人资料页面
 * 路径：pages/edit-profile/edit-profile
 *
 * 功能：昵称、个人简介、性别、生日编辑
 * API：PUT /auth/users/profile
 */
const { get, put } = require('../../utils/request');

Page({
  data: {
    nickname: '',
    bio: '',
    gender: '',       // male | female | secret
    birthday: '',     // YYYY-MM-DD
    avatarUrl: '',
    saving: false,
    loading: true,

    // 性别选项
    genderOptions: [
      { value: 'male', label: '男' },
      { value: 'female', label: '女' },
      { value: 'secret', label: '保密' },
    ],
    genderLabels: {
      male: '男',
      female: '女',
      secret: '保密',
    },

    // 生日选择器
    birthDate: '',
  },

  onLoad() {
    this.loadProfile();
  },

  async loadProfile() {
    this.setData({ loading: true });
    try {
      const user = await get('/auth/me');
      this.setData({
        nickname: user.nickname || '',
        bio: user.bio || '',
        gender: user.gender || '',
        birthday: user.birthday || '',
        avatarUrl: user.avatar_url || '',
        birthDate: user.birthday || '',
        loading: false,
      });
    } catch (e) {
      console.error('加载用户资料失败', e);
      this.setData({ loading: false });
      wx.showToast({
        title: (e && e.message) || '资料加载失败，请重试',
        icon: 'none',
      });
    }
  },

  // ========== 编辑操作 ==========

  onNicknameInput(e) {
    this.setData({ nickname: e.detail.value });
  },

  onBioInput(e) {
    // 个人简介限制200字
    const value = e.detail.value.slice(0, 200);
    this.setData({ bio: value });
  },

  onGenderTap() {
    const { gender, genderOptions, genderLabels } = this.data;
    const labels = genderOptions.map(opt => opt.label);
    const currentIndex = genderOptions.findIndex(opt => opt.value === gender);
    wx.showActionSheet({
      itemList: labels,
      current: currentIndex >= 0 ? currentIndex : 2,
      success: (res) => {
        const selected = genderOptions[res.tapIndex];
        this.setData({ gender: selected.value });
      },
    });
  },

  onBirthdayChange(e) {
    this.setData({
      birthday: e.detail.value,
      birthDate: e.detail.value,
    });
  },

  // 保存
  async onSave() {
    const { nickname, bio, gender, birthday, saving } = this.data;

    if (saving) return;

    // 校验
    if (!nickname.trim()) {
      wx.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }
    if (nickname.trim().length > 20) {
      wx.showToast({ title: '昵称最多20个字符', icon: 'none' });
      return;
    }

    this.setData({ saving: true });
    wx.showLoading({ title: '保存中...' });

    try {
      await put('/auth/users/profile', {
        nickname: nickname.trim(),
        bio: bio.trim(),
        gender: gender || '',
        birthday: birthday || '',
      });

      wx.hideLoading();
      wx.showToast({ title: '保存成功', icon: 'success' });

      // 通知上一页刷新
      const pages = getCurrentPages();
      if (pages.length > 1) {
        const prevPage = pages[pages.length - 2];
        if (prevPage && typeof prevPage.loadProfile === 'function') {
          prevPage.loadProfile();
        }
      }

      setTimeout(() => {
        wx.navigateBack();
      }, 1200);
    } catch (e) {
      wx.hideLoading();
      console.error('保存失败', e);
      wx.showToast({ title: '保存失败，请重试', icon: 'none' });
    } finally {
      this.setData({ saving: false });
    }
  },
});
