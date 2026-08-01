const { CLOUD_ENV_ID } = require('../config');
const { post } = require('./request');

const MAX_CHECK_SIZE = 1024 * 1024;

function getFileInfo(filePath) {
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().getFileInfo({ filePath, success: resolve, fail: reject });
  });
}

function compressImage(filePath) {
  if (typeof wx.compressImage !== 'function') return Promise.resolve(filePath);
  return new Promise((resolve) => {
    wx.compressImage({
      src: filePath,
      quality: 60,
      success: (result) => resolve(result.tempFilePath || filePath),
      fail: () => resolve(filePath),
    });
  });
}

function readBase64(filePath) {
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().readFile({ filePath, encoding: 'base64', success: (res) => resolve(res.data), fail: reject });
  });
}

function safeExtension(filePath) {
  const matched = String(filePath || '').match(/\.([a-zA-Z0-9]{2,5})(?:\?|$)/);
  const ext = matched ? matched[1].toLowerCase() : 'jpg';
  return ['jpg', 'jpeg', 'png', 'webp'].includes(ext) ? ext : 'jpg';
}

function randomName() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

async function uploadImage(filePath, purpose = 'ugc') {
  if (!filePath || filePath.startsWith('cloud://')) return filePath;

  const checkedPath = await compressImage(filePath);
  const info = await getFileInfo(checkedPath);
  if (info.size > MAX_CHECK_SIZE) {
    throw new Error('图片压缩后仍超过1MB，请重新选择');
  }

  const contentType = safeExtension(checkedPath) === 'png' ? 'image/png' : 'image/jpeg';
  await post('/content-security/image', {
    image_base64: await readBase64(checkedPath),
    content_type: contentType,
  });

  const cloudPath = `ugc/${purpose}/${new Date().toISOString().slice(0, 10)}/${randomName()}.${safeExtension(filePath)}`;
  const result = await wx.cloud.uploadFile({
    config: { env: CLOUD_ENV_ID },
    cloudPath,
    filePath: checkedPath,
  });
  if (!result.fileID) throw new Error('图片上传失败');
  return result.fileID;
}

async function uploadImages(filePaths, purpose = 'ugc') {
  return Promise.all((filePaths || []).map((filePath) => uploadImage(filePath, purpose)));
}

module.exports = { uploadImage, uploadImages };
