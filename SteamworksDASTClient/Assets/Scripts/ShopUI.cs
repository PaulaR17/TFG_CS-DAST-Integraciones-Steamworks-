using UnityEngine;
using UnityEngine.UI;

public class ShopUI : MonoBehaviour
{
    public Button buyBoostButton;
    public Button closeShopButton;
    public int boostCost = 50;

    void Start()
    {
        buyBoostButton.onClick.AddListener(OnBuyBoost);
        closeShopButton.onClick.AddListener(() => GameManager.Instance.ToggleShop());
    }

    void OnBuyBoost()
    {
        buyBoostButton.interactable = false;

        ApiClient.Instance.InitTransaction("Speed Boost", boostCost,
            onSuccess: (orderId) =>
            {
                ApiClient.Instance.FinalizeTransaction(orderId,
                    onSuccess: () =>
                    {
                        Debug.Log("[Shop] Compra completada");
                        GameManager.Instance.OnPurchaseSuccess(boostCost);
                        buyBoostButton.interactable = true;
                    },
                    onError: (err) =>
                    {
                        Debug.LogError("[Shop] Finalize error: " + err);
                        buyBoostButton.interactable = true;
                    });
            },
            onError: (err) =>
            {
                Debug.LogError("[Shop] Init error: " + err);
                buyBoostButton.interactable = true;
            });
    }
}