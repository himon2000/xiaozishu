const { post } = require('./request');

const REASONS = [
  { label: '垃圾广告', value: 'spam' },
  { label: '虚假信息', value: 'fake' },
  { label: '不适当内容', value: 'inappropriate' },
  { label: '骚扰攻击', value: 'harassment' },
  { label: '侵权内容', value: 'copyright' },
  { label: '其他', value: 'other' },
];

function reportContent(targetType, targetId) {
  return new Promise((resolve) => {
    wx.showActionSheet({
      itemList: REASONS.map((item) => item.label),
      success: async ({ tapIndex }) => {
        try {
          await post('/reports', {
            target_type: targetType,
            target_id: targetId,
            reason: REASONS[tapIndex].value,
          });
          wx.showToast({ title: '举报已提交', icon: 'success' });
          resolve(true);
        } catch (error) {
          wx.showToast({ title: error.message || '提交失败', icon: 'none' });
          resolve(false);
        }
      },
      fail: () => resolve(false),
    });
  });
}

module.exports = { reportContent };
