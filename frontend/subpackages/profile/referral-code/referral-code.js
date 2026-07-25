/**
 * 飞花令牌页面
 * 路径：subpackages/profile/referral-code/referral-code
 * 功能：展示我的飞花令牌、填写飞花令牌兑换
 */
const { get, post } = require('../../../utils/request');

Page({
  data: {
    myCode: '',          // 我的飞花令牌
    totalInvited: 0,     // 已邀请人数
    inviteTreeDepth: 0,  // 邀请树深度
    // 兑换相关
    showRedeemModal: false,
    redeemCode: '',
    redeemLoading: false,
    hasRedeemed: false,   // 是否已兑换过
    redeemResult: null,   // 兑换结果
    // 分享相关
    canShare: true,
  },

  onLoad() {
    // 检查是否已使用过飞花令牌
    const app = getApp();
    this.setData({ hasRedeemed: app.globalData.userInfo?.referrer_openid ? true : false });
  },

  onShow() {
    this.loadReferralInfo();
  },

  async loadReferralInfo() {
    wx.showLoading({ title: '加载中...' });
    try {
      // 获取我的飞花令牌信息
      const res = await get('/auth/referral-code');
      if (res) {
        this.setData({
          myCode: res.referral_code || '',
          totalInvited: res.total_invited || 0,
          inviteTreeDepth: res.invite_tree_depth || 0,
        });
      }
    } catch (e) {
      console.error('获取飞花令牌失败', e);
      wx.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  // 复制飞花令牌
  onCopyCode() {
    if (!this.data.myCode) return;
    wx.setClipboardData({
      data: this.data.myCode,
      success: () => {
        wx.showToast({ title: '飞花令牌已复制', icon: 'success' });
      },
    });
  },

  // 分享小程序
  onShareAppMessage() {
    const { myCode } = this.data;
    return {
      title: '邀请你加入小紫薯',
      path: `/pages/splash/splash?ref=${myCode}`,
      imageUrl: '/assets/logo.png',
    };
  },

  // 打开兑换弹窗
  onOpenRedeem() {
    this.setData({ showRedeemModal: true, redeemCode: '', redeemResult: null });
  },

  // 关闭兑换弹窗
  onCloseRedeem() {
    this.setData({ showRedeemModal: false, redeemCode: '', redeemResult: null });
  },

  // 输入飞花令牌
  onRedeemInput(e) {
    this.setData({ redeemCode: e.detail.value.toUpperCase() });
  },

  // 提交兑换
  async onSubmitRedeem() {
    const code = this.data.redeemCode.trim();
    if (!code) {
      wx.showToast({ title: '请输入飞花令牌', icon: 'none' });
      return;
    }
    if (code.length < 6) {
      wx.showToast({ title: '飞花令牌格式不正确', icon: 'none' });
      return;
    }

    this.setData({ redeemLoading: true });
    try {
      const res = await post('/auth/users/redeem-referral', { code });
      if (res.success) {
        this.setData({
          redeemResult: { success: true, message: res.message },
          hasRedeemed: true,
        });
        // 更新全局用户信息
        const app = getApp();
        if (app.globalData.userInfo) {
          app.globalData.userInfo.referrer_openid = res.referrer_openid;
        }
      } else {
        this.setData({ redeemResult: { success: false, message: res.message } });
      }
    } catch (e) {
      console.error('兑换失败', e);
      this.setData({ redeemResult: { success: false, message: e.errMsg || '兑换失败' } });
    } finally {
      this.setData({ redeemLoading: false });
    }
  },

  // 关闭结果弹窗
  onCloseResult() {
    this.setData({ showRedeemModal: false, redeemResult: null });
  },

  // 奖励规则说明
  onShowRules() {
    wx.showModal({
      title: '🎁 推荐奖励规则',
      content: `【邀请奖励】
每成功邀请1位新用户：
• 邀请人获得：+500积分、+15修为
• 被邀请人获得：+500积分

【兑换条件】
• 每个用户只能使用1次飞花令牌
• 不能使用自己的飞花令牌
• 飞花令牌有效期：无限制

【奖励发放】
• 积分实时到账
• 修为将在交易完成后发放`,
      showCancel: false,
      confirmText: '我知道了',
    });
  },
});
