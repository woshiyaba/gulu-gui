<script>
	import { silentLogin } from '@/utils/auth'
	import { preloadMapData } from '@/utils/mapPreload'

	export default {
		onLaunch: function() {
			console.log('App Launch')
			silentLogin()
			setTimeout(() => {
				preloadMapData().catch(() => {})
			}, 1200)
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style>
	/*每个页面公共css */
</style>
