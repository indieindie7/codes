using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class BasicRoad : MonoBehaviour
{

  //  public Connections c1;
    public Vector3 p1, p2, p3, p4;
 //   public Connections c2;
    public Dictionary<Connections, float> conections = new Dictionary<Connections, float>();
    public float distance;

    public void set(Vector3 p1,  Vector3 p2, Vector3 p3, Vector3 p4, float distance)
    {
        this.p1 = p1;
        this.p4 = p4;
        this.p2 = p2;
        this.p3 = p3;
        this.distance = distance;
    }

}
