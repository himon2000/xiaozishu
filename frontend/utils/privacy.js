function ensurePrivacyAuthorized() {
  if (typeof wx.requirePrivacyAuthorize !== 'function') return Promise.resolve();
  return new Promise((resolve, reject) => {
    wx.requirePrivacyAuthorize({
      success: resolve,
      fail: () => {
        wx.showModal({
          title: '需要隐私授权',
          content: '选择图片前，请先阅读并同意小程序隐私保护指引。',
          confirmText: '查看指引',
          success: (result) => {
            if (result.confirm && typeof wx.openPrivacyContract === 'function') {
              wx.openPrivacyContract({});
            }
          },
        });
        reject(new Error('未获得隐私授权'));
      },
    });
  });
}

module.exports = { ensurePrivacyAuthorized };
