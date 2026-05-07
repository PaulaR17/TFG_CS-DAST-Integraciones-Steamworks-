using UnityEngine;

public class PowerUp : MonoBehaviour
{
    public string itemName = "Energy Cell";
    public string quality = "common";
    public float fallSpeed = 1.5f;

    void Update()
    {
        transform.Translate(Vector3.down * fallSpeed * Time.deltaTime);
    }

    void OnTriggerEnter2D(Collider2D other)
    {
        if (other.CompareTag("Player"))
        {
            GameManager.Instance.OnPickupPowerUp(itemName, quality);
            Destroy(gameObject);
        }
    }
}