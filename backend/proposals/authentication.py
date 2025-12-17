from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthenticationのCSRFチェックをスキップするカスタム認証クラス

    開発環境やSPA（Single Page Application）での使用を想定
    本番環境では適切なCSRF保護を実装することを推奨
    """

    def enforce_csrf(self, request):
        """
        CSRFチェックをスキップ
        """
        return  # CSRFチェックを実行しない
