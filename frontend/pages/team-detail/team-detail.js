/**
 * 组队详情页
 * 路径: pages/team-detail/team-detail
 */
const { get, post, del } = require('../../utils/request');

Page({
  data: {
    teamId: '',
    team: null,
    members: [],
    isCreator: false,
    isMember: false,
    loading: true,
  },

  onLoad(options) {
    if (!options.team_id) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      wx.navigateBack();
      return;
    }
    this.setData({ teamId: options.team_id });
    this.loadTeamDetail();
  },

  onShow() {
    // 每次显示时刷新（可能加入了新成员）
    if (this.data.teamId) {
      this.loadTeamDetail();
    }
  },

  async loadTeamDetail() {
    this.setData({ loading: true });
    try {
      const res = await get(`/teams/${this.data.teamId}`);
      const app = getApp();
      const myOpenid = app.globalData.userInfo?.openid || '';

      this.setData({
        team: res,
        members: res.members || [],
        isCreator: res.creator?.openid === myOpenid,
        isMember: (res.members || []).some(m => m.openid === myOpenid),
        loading: false,
      });
    } catch (e) {
      console.error('加载组队详情失败', e);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  // 加入组队
  async onJoinTeam() {
    try {
      const res = await post(`/teams/${this.data.teamId}/join`);
      wx.showToast({ title: '加入成功！', icon: 'success' });
      this.loadTeamDetail();
    } catch (e) {
      wx.showToast({ title: e.detail || '加入失败', icon: 'none' });
    }
  },

  // 离开组队
  async onLeaveTeam() {
    wx.showModal({
      title: '确认离开',
      content: '确定要离开该组队吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await post(`/teams/${this.data.teamId}/leave`);
            wx.showToast({ title: '已离开', icon: 'success' });
            this.loadTeamDetail();
          } catch (e) {
            wx.showToast({ title: e.detail || '操作失败', icon: 'none' });
          }
        }
      }
    });
  },

  // 解散组队（仅创建者）
  async onDeleteTeam() {
    wx.showModal({
      title: '确认解散',
      content: '确定要解散该组队吗？此操作不可撤销！',
      success: async (res) => {
        if (res.confirm) {
          try {
            await del(`/teams/${this.data.teamId}`);
            wx.showToast({ title: '已解散', icon: 'success' });
            setTimeout(() => {
              wx.navigateBack();
            }, 1500);
          } catch (e) {
            wx.showToast({ title: e.detail || '操作失败', icon: 'none' });
          }
        }
      }
    });
  },

  // 查看用户主页
  onViewProfile(e) {
    const openid = e.currentTarget.dataset.openid;
    wx.navigateTo({ url: `/subpackages/mentor/mentor-apply/mentor-apply?openid=${openid}` });
  },
});
