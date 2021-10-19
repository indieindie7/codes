using playerInventory;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
public enum spotPlace
{
    hand, back//head,hand
}

public class ItemLevel : MonoBehaviour
{
    public Vector2Int size;
    public spotPlace spot;
    public bool canStore;
    //[Range(0, 1)]
    //public float tempProtection;
    internal Item ItemOnSpot;
    internal List<Item> ItemHelds;
    internal Item imageVersion;
    internal delegate void Action(Transform t);
    internal Action myAction;

public virtual void Start()
    {
        if (canStore) ItemHelds = new List<Item>();
        myAction = delegate(Transform t) { print(t.name); };
    }
}
