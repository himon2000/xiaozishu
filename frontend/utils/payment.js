/**
 * 微信支付工具
 */
const { request } = require('./request');

/**
 * 调起微信支付
 * @param {string} orderId - 订单ID
 * @returns {Promise<{success: boolean, reason?: string}>}
 */
function requestPayment(orderId) {
  return new Promise(async (resolve, reject) => {
    try {
      // 1. 向后端请求支付参数
      const payParams = await request({
        url: `/orders/${orderId}/pay`,
        method: 'POST',
      });

      // 2. 调起微信支付
      wx.requestPayment({
        timeStamp: payParams.timeStamp,
        nonceStr: payParams.nonceStr,
        package: payParams.package,
        signType: payParams.signType || 'RSA',
        paySign: payParams.paySign,
        success: (res) => {
          resolve({ success: true });
        },
        fail: (err) => {
          if (err.errMsg && err.errMsg.includes('cancel')) {
            resolve({ success: false, reason: 'cancelled' });
          } else {
            resolve({ success: false, reason: 'payment_failed', detail: err });
          }
        },
      });
    } catch (e) {
      reject(e);
    }
  });
}

/**
 * 查询支付结果
 */
async function checkPaymentResult(orderId) {
  const { request } = require('./request');
  const order = await request({ url: `/orders/${orderId}` });
  return order;
}

module.exports = { requestPayment, checkPaymentResult };
