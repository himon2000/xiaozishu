/**
 * 大虾卡片组件
 * components/mentor-card/mentor-card.js
 */
Component({
  properties: {
    mentor: { type: Object, value: null },
    compact: { type: Boolean, value: false },
  },

  methods: {
    onTap() {
      const { openid } = this.data.mentor;
      if (openid) {
        wx.navigateTo({
          url: `/subpackages/mentor/mentor-apply/mentor-apply?openid=${openid}`,
        });
      }
    },
  },
});
