using UnityEngine;

public class Bullet : MonoBehaviour
{
    public float speed = 12f;
    public float lifeTime = 2f;

    void Start()
    {
        GetComponent<Rigidbody2D>().velocity = Vector2.up * speed;
        Destroy(gameObject, lifeTime);
    }

    void OnTriggerEnter2D(Collider2D other)
    {
        if (other.CompareTag("Enemy"))
        {
            other.GetComponent<Enemy>()?.Die();
            Destroy(gameObject);
        }
    }
}