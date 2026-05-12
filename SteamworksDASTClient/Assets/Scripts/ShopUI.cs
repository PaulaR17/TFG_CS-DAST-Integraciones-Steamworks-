using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Tienda integrada del juego. Vende paquetes de creditos virtuales
/// (modelo coherente con la microtransaccion ISteamMicroTxn de Valve, donde
/// el usuario paga con dinero real y recibe moneda dentro del juego).
///
/// El flujo es:
///   1. POST /transactions/init   -> crea la orden pendiente
///   2. POST /vulnerable/transactions/finalize con approved_by_client=true
///                                -> backend confia en el cliente y abona credits
///
/// La vulnerabilidad demostrada es API6:2023: el backend acepta la aprobacion
/// del cliente sin verificar el pago real con Steam Web API. Cualquiera puede
/// reclamar el paquete sin haber pagado nada.
/// </summary>
public class ShopUI : MonoBehaviour
{
    [Header("UI")]
    public Button buyPackButton;
    public Button closeShopButton;

    [Header("Paquete a vender")]
    [Tooltip("Identificador legible del paquete que se envia al backend.")]
    public string packItemName = "Credit Pack 50";

    [Tooltip("Cantidad de creditos que el cliente recibe si la transaccion se aprueba.")]
    public int packAmount = 50;

    void Start()
    {
        buyPackButton.onClick.AddListener(OnBuyPack);
        closeShopButton.onClick.AddListener(() => GameManager.Instance.ToggleShop());
    }

    void OnBuyPack()
    {
        buyPackButton.interactable = false;

        ApiClient.Instance.InitTransaction(packItemName, packAmount,
            onSuccess: (orderId) =>
            {
                ApiClient.Instance.FinalizeTransaction(orderId,
                    onSuccess: () =>
                    {
                        Debug.Log($"[Shop] Compra completada: +{packAmount} credits");
                        GameManager.Instance.OnPurchaseSuccess(packAmount);
                        buyPackButton.interactable = true;
                    },
                    onError: (err) =>
                    {
                        Debug.LogError("[Shop] Finalize error: " + err);
                        buyPackButton.interactable = true;
                    });
            },
            onError: (err) =>
            {
                Debug.LogError("[Shop] Init error: " + err);
                buyPackButton.interactable = true;
            });
    }
}